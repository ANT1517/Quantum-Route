// The visual hero. react-leaflet (SVG renderer) over darkened OSM tiles in live mode; falls back to a plain
// <canvas> (no basemap) in demo/offline mode, when tiles fail (T40), or when coordinates are planar
// (SynthCity km / CVRPLIB), prop `plain`. Route paths glow (drop-shadow on route paths only, off above 40 lines).
import L from "leaflet";
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { Circle, CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap, useMapEvents, ZoomControl } from "react-leaflet";
import type { ResultJSON } from "../types/result";
import type { Customer } from "../api/types";
import { INCIDENT, vcColor, vehicleColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";

export type LatLon = [number, number];

export interface MapLine {
  geometry: LatLon[];
  color: string;
  weight?: number;
  dashed?: boolean;
  label?: string;
  opacity?: number;
  /** Draw with the glow halo (default: true for extra lines). */
  glow?: boolean;
}

export interface MapPoint {
  lat: number;
  lon: number;
  label?: string;
  color?: string;
}

export interface RouteMapProps {
  routes?: ResultJSON["routes"];
  edgeFlows?: ResultJSON["edge_flows"];
  showFlows?: boolean;
  customers?: Customer[];
  depot?: LatLon | null;
  incident?: { center: LatLon; radius_m: number } | null;
  extraLines?: MapLine[];
  points?: MapPoint[];
  /** Planar coordinates (not lat/lon): always use the canvas renderer. */
  plain?: boolean;
  onMapClick?: (lat: number, lon: number) => void;
  height?: number | string;
  className?: string;
  /** Scale flow-edge glow by fleet flow (Fleet impact). */
  flowGlow?: boolean;
  ariaLabel?: string;
}

type Kind = "flow" | "route" | "extra";

interface Drawable {
  lines: Array<MapLine & { kind: Kind; flowT?: number }>;
  customers: Customer[];
  depot: LatLon | null;
  incident: { center: LatLon; radius_m: number } | null;
  points: MapPoint[];
}

const GLOW_MAX_LINES = 40;

function useDrawable(p: RouteMapProps): Drawable {
  return useMemo(() => {
    const lines: Drawable["lines"] = [];
    if (p.showFlows && p.edgeFlows?.length) {
      const maxFlow = Math.max(1e-9, ...p.edgeFlows.map((e) => e.fleet_flow));
      // flowGlow: only the GLOW_MAX_LINES busiest edges glow (halo scaled by fleet flow), so it stays fast
      const glowSet = new Set<number>(
        p.flowGlow
          ? p.edgeFlows
              .map((e, i) => [e.fleet_flow, i] as const)
              .filter(([f]) => f > 0)
              .sort((a, b) => b[0] - a[0])
              .slice(0, GLOW_MAX_LINES - (p.routes?.length ?? 0) - (p.extraLines?.length ?? 0))
              .map(([, i]) => i)
          : [],
      );
      p.edgeFlows.forEach((e, idx) => {
        lines.push({
          kind: "flow",
          geometry: e.geometry,
          color: vcColor(e.vc_ratio),
          weight: 1.5 + (6 * e.fleet_flow) / maxFlow,
          opacity: 0.8,
          flowT: e.fleet_flow / maxFlow,
          glow: glowSet.has(idx),
          label: `flow ${e.fleet_flow} · V/C ${e.vc_ratio}`,
        });
      });
    }
    (p.routes ?? []).forEach((r, i) => {
      lines.push({ kind: "route", geometry: r.geometry, color: vehicleColor(i), weight: 3, label: `Vehicle ${r.vehicle}`, glow: true });
    });
    for (const l of p.extraLines ?? []) lines.push({ glow: true, ...l, kind: "extra" });
    const firstRoute = p.routes?.find((r) => r.geometry?.length);
    const depot = p.depot ?? (firstRoute ? firstRoute.geometry[0] : null);
    return { lines, customers: p.customers ?? [], depot, incident: p.incident ?? null, points: p.points ?? [] };
  }, [p.showFlows, p.edgeFlows, p.flowGlow, p.routes, p.extraLines, p.customers, p.depot, p.incident, p.points]);
}

function allPoints(d: Drawable): LatLon[] {
  const pts: LatLon[] = [];
  d.lines.forEach((l) => l.geometry.forEach((g) => pts.push(g)));
  d.customers.forEach((c) => pts.push([c.lat, c.lon]));
  d.points.forEach((c) => pts.push([c.lat, c.lon]));
  if (d.depot) pts.push(d.depot);
  return pts.filter((x) => Array.isArray(x) && Number.isFinite(x[0]) && Number.isFinite(x[1]));
}

const depotIcon = L.divIcon({
  className: "qr-depot-icon",
  html: '<div style="width:14px;height:14px;border-radius:4px;background:#fff;border:2px solid #030304;box-shadow:0 0 0 1px rgba(255,255,255,.6),0 0 14px rgba(255,255,255,.75)"></div>',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

function FitBounds({ pts }: { pts: LatLon[] }) {
  const map = useMap();
  const key = pts.length ? `${pts.length}:${pts[0].join(",")}:${pts[pts.length - 1].join(",")}` : "";
  useEffect(() => {
    if (!pts.length) return;
    const b = L.latLngBounds(pts.map((p) => L.latLng(p[0], p[1])));
    if (b.isValid()) map.fitBounds(b.pad(0.1), { animate: false });
  }, [key, map]);
  return null;
}

/** invalidateSize() after layout changes (sub-nav switches, drawer, resize, navigation). */
function InvalidateOnResize() {
  const map = useMap();
  useEffect(() => {
    const el = map.getContainer();
    const t = setTimeout(() => map.invalidateSize(), 50);
    if (typeof ResizeObserver === "undefined") return () => clearTimeout(t);
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(el);
    return () => {
      clearTimeout(t);
      ro.disconnect();
    };
  }, [map]);
  return null;
}

function ClickHandler({ onClick }: { onClick?: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onClick?.(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// ------------------------------------------------------------------ canvas fallback

function CanvasMap({ d, plain, onMapClick, glow, ariaLabel }: { d: Drawable; plain: boolean; onMapClick?: (a: number, b: number) => void; glow: boolean; ariaLabel: string }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const tfRef = useRef<{ toXY: (p: LatLon) => [number, number]; toLL: (x: number, y: number) => LatLon } | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const update = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    update();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv || size.w === 0 || size.h === 0) return;
    const dpr = window.devicePixelRatio || 1;
    cv.width = size.w * dpr;
    cv.height = size.h * dpr;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#06080A";
    ctx.fillRect(0, 0, size.w, size.h);
    // faint street grid texture
    ctx.strokeStyle = "#0C1014";
    ctx.lineWidth = 1;
    for (let x = 0.5; x < size.w; x += 36) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, size.h);
      ctx.stroke();
    }
    for (let y = 0.5; y < size.h; y += 36) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(size.w, y);
      ctx.stroke();
    }

    const pts = allPoints(d);
    if (d.incident) {
      const r = plain ? d.incident.radius_m / 1000 : d.incident.radius_m / 111320;
      pts.push([d.incident.center[0] - r, d.incident.center[1] - r], [d.incident.center[0] + r, d.incident.center[1] + r]);
    }
    if (!pts.length) {
      ctx.fillStyle = "#5A616B";
      ctx.font = "11px 'JetBrains Mono', monospace";
      ctx.fillText("NOTHING TO DRAW YET", 16, 24);
      tfRef.current = null;
      return;
    }
    const lats = pts.map((p) => p[0]);
    const lons = pts.map((p) => p[1]);
    const minA = Math.min(...lats),
      maxA = Math.max(...lats),
      minB = Math.min(...lons),
      maxB = Math.max(...lons);
    const midA = (minA + maxA) / 2;
    const kx = plain ? 1 : Math.cos((midA * Math.PI) / 180); // squash longitude
    const spanX = Math.max(1e-9, (maxB - minB) * kx);
    const spanY = Math.max(1e-9, maxA - minA);
    const pad = 28;
    const s = Math.min((size.w - 2 * pad) / spanX, (size.h - 2 * pad) / spanY);
    const offX = (size.w - spanX * s) / 2;
    const offY = (size.h - spanY * s) / 2;
    const toXY = (p: LatLon): [number, number] => [offX + (p[1] - minB) * kx * s, size.h - offY - (p[0] - minA) * s];
    const toLL = (x: number, y: number): LatLon => [minA + (size.h - offY - y) / s, minB + (x - offX) / (kx * s)];
    tfRef.current = { toXY, toLL };

    const path = (g: LatLon[]) => {
      ctx.beginPath();
      g.forEach((pt, i) => {
        const [x, y] = toXY(pt);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
    };
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    // street underlay (#12161B) from every drawn geometry
    for (const l of d.lines) {
      if (l.geometry.length < 2) continue;
      path(l.geometry);
      ctx.strokeStyle = "#12161B";
      ctx.lineWidth = (l.weight ?? 3) + 5;
      ctx.stroke();
    }
    if (d.incident) {
      const [cx, cy] = toXY(d.incident.center);
      const r = Math.max(6, (plain ? d.incident.radius_m / 1000 : d.incident.radius_m / 111320) * s);
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 1.4);
      g.addColorStop(0, "rgba(255,181,71,0.35)");
      g.addColorStop(0.6, "rgba(255,181,71,0.12)");
      g.addColorStop(1, "rgba(255,181,71,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(cx, cy, r * 1.4, 0, Math.PI * 2);
      ctx.fill();
    }
    for (const l of d.lines) {
      if (l.geometry.length < 2) continue;
      path(l.geometry);
      ctx.strokeStyle = l.color;
      ctx.globalAlpha = l.opacity ?? 0.95;
      ctx.lineWidth = l.weight ?? 3;
      ctx.setLineDash(l.dashed ? [8, 6] : []);
      const g = glow && !!l.glow;
      ctx.shadowColor = g ? l.color : "transparent";
      ctx.shadowBlur = g ? (l.kind === "flow" ? 2 + 8 * (l.flowT ?? 0) : 8) : 0;
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
    ctx.shadowColor = "transparent";
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    if (d.incident) {
      const [cx, cy] = toXY(d.incident.center);
      const r = Math.max(6, (plain ? d.incident.radius_m / 1000 : d.incident.radius_m / 111320) * s);
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = INCIDENT;
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.setLineDash([]);
    }
    for (const c of d.customers) {
      const [x, y] = toXY([c.lat, c.lon]);
      ctx.beginPath();
      ctx.arc(x, y, 3.2, 0, Math.PI * 2);
      ctx.fillStyle = "#030304";
      ctx.fill();
      ctx.strokeStyle = "#CFD3D8";
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
    for (const p of d.points) {
      const [x, y] = toXY([p.lat, p.lon]);
      ctx.shadowColor = p.color ?? "#4FE3D1";
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.arc(x, y, 6, 0, Math.PI * 2);
      ctx.fillStyle = p.color ?? "#4FE3D1";
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = "#030304";
      ctx.lineWidth = 2;
      ctx.stroke();
      if (p.label) {
        ctx.font = "11px 'JetBrains Mono', monospace";
        const w = ctx.measureText(p.label).width + 12;
        ctx.fillStyle = "rgba(10,12,15,.92)";
        ctx.strokeStyle = "#262B33";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect?.(x + 10, y - 22, w, 18, 4);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = "#F5F6F7";
        ctx.fillText(p.label, x + 16, y - 9);
      }
    }
    if (d.depot) {
      const [x, y] = toXY(d.depot);
      ctx.shadowColor = "rgba(255,255,255,.85)";
      ctx.shadowBlur = 14;
      ctx.fillStyle = "#FFFFFF";
      ctx.beginPath();
      ctx.roundRect?.(x - 7, y - 7, 14, 14, 4);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = "#030304";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect?.(x - 5, y - 5, 10, 10, 3);
      ctx.stroke();
    }
  }, [d, size, plain, glow]);

  const click = (e: MouseEvent<HTMLCanvasElement>) => {
    if (!onMapClick || !tfRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const [a, b] = tfRef.current.toLL(e.clientX - rect.left, e.clientY - rect.top);
    onMapClick(a, b);
  };

  return (
    <div ref={wrapRef} className="relative h-full w-full">
      <canvas
        ref={canvasRef}
        onClick={click}
        role="img"
        aria-label={ariaLabel}
        style={{ width: "100%", height: "100%", display: "block", cursor: onMapClick ? "crosshair" : "default" }}
      />
    </div>
  );
}

// ------------------------------------------------------------------ main component

export default function RouteMap(props: RouteMapProps) {
  const demo = useDemoMode();
  const d = useDrawable(props);
  const [tilesFailed, setTilesFailed] = useState(false);
  const stats = useRef({ errors: 0, loads: 0 });
  const pts = useMemo(() => allPoints(d), [d]);
  const height = props.height ?? 480;
  const useCanvas = props.plain || tilesFailed || demo;
  const center: LatLon = pts[0] ?? [17.4, 78.47];
  const glowCount = d.lines.filter((l) => l.glow).length;
  const glow = glowCount <= GLOW_MAX_LINES;
  const nRoutes = d.lines.filter((l) => l.kind === "route").length;
  const ariaLabel =
    props.ariaLabel ??
    `Map: ${nRoutes ? `${nRoutes} vehicle routes, ` : ""}${d.customers.length} customers${d.depot ? ", depot" : ""}${d.incident ? `, incident zone of ${d.incident.radius_m} m` : ""}${d.lines.some((l) => l.kind === "extra") ? ", path overlays" : ""}.`;

  const onTileError = () => {
    stats.current.errors += 1;
    if ((stats.current.errors >= 2 && stats.current.loads === 0) || stats.current.errors >= 12) setTilesFailed(true);
  };

  return (
    <div className={`relative overflow-hidden ${glow ? "qr-glow" : ""} ${props.className ?? ""}`} style={{ height, background: "var(--map-bg)" }}>
      {useCanvas ? (
        <>
          <CanvasMap d={d} plain={!!props.plain} onMapClick={props.onMapClick} glow={glow} ariaLabel={ariaLabel} />
          <div className="chip absolute bottom-2 left-2 z-[400]" style={{ background: "rgba(3,3,4,.75)" }}>
            {props.plain ? "offline map · planar coordinates" : demo ? "offline map · demo data" : "offline map · tiles unavailable"}
          </div>
        </>
      ) : (
        <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom zoomControl={false} zoomSnap={0.25} zoomDelta={0.5} aria-label={ariaLabel}>
          {/* CARTO dark_all now answers with an "API key required" image, so the OSM tiles used before are darkened
              with a CSS filter on the tile pane only (.qr-dark-tiles); routes and markers are unaffected. */}
          <TileLayer
            className="qr-dark-tiles"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
            eventHandlers={{
              tileerror: onTileError,
              tileload: () => {
                stats.current.loads += 1;
              },
            }}
          />
          <ZoomControl position="bottomright" />
          <FitBounds pts={pts} />
          <InvalidateOnResize />
          <ClickHandler onClick={props.onMapClick} />
          {d.incident && (
            <>
              <Circle
                center={d.incident.center}
                radius={d.incident.radius_m * 1.4}
                interactive={false}
                pathOptions={{ stroke: false, fillColor: "url(#qr-incident-grad)", fillOpacity: 1 }}
              />
              <Circle center={d.incident.center} radius={d.incident.radius_m} pathOptions={{ color: INCIDENT, weight: 1.5, dashArray: "5 4", fill: false }}>
                <Tooltip>Incident zone (simulated)</Tooltip>
              </Circle>
            </>
          )}
          {d.lines.map((l, i) => (
            <Polyline
              key={`${l.kind}-${i}`}
              positions={l.geometry}
              pathOptions={{
                color: l.color,
                weight: l.weight ?? 3,
                opacity: l.opacity ?? 0.95,
                dashArray: l.dashed ? "8 6" : undefined,
                className: l.glow ? "qr-route" : undefined,
                lineCap: "round",
                lineJoin: "round",
              }}
              eventHandlers={
                l.glow
                  ? {
                      add: (e) => {
                        const el = (e.target as L.Path).getElement() as SVGElement | undefined;
                        if (!el) return;
                        el.style.color = l.color;
                        if (l.kind === "flow") el.style.filter = `drop-shadow(0 0 ${(1.5 + 5 * (l.flowT ?? 0)).toFixed(1)}px currentColor)`;
                      },
                    }
                  : undefined
              }
            >
              {l.label && <Tooltip sticky>{l.label}</Tooltip>}
            </Polyline>
          ))}
          {d.customers.map((c) => (
            <CircleMarker key={`c-${c.id}`} center={[c.lat, c.lon]} radius={3.5} pathOptions={{ color: "#CFD3D8", weight: 1.2, fillColor: "#030304", fillOpacity: 1 }}>
              <Tooltip>{`Customer ${c.id} · demand ${c.demand}`}</Tooltip>
            </CircleMarker>
          ))}
          {d.points.map((p, i) => (
            <CircleMarker key={`p-${i}`} center={[p.lat, p.lon]} radius={7} pathOptions={{ color: "#030304", weight: 2, fillColor: p.color ?? "#4FE3D1", fillOpacity: 1, className: "qr-route" }}
              eventHandlers={{
                add: (e) => {
                  const el = (e.target as L.Path).getElement() as SVGElement | undefined;
                  if (el) el.style.color = p.color ?? "#4FE3D1";
                },
              }}
            >
              {p.label && (
                <Tooltip permanent direction="top">
                  {p.label}
                </Tooltip>
              )}
            </CircleMarker>
          ))}
          {d.depot && (
            <Marker position={d.depot} icon={depotIcon} keyboard={false}>
              <Tooltip>Depot</Tooltip>
            </Marker>
          )}
        </MapContainer>
      )}
    </div>
  );
}
