// The visual hero. react-leaflet over OSM tiles; falls back to a plain <canvas> (no basemap)
// when tiles fail (T40) or when coordinates are planar (SynthCity km / CVRPLIB), prop `plain`.
import L from "leaflet";
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { Circle, CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import type { ResultJSON } from "../types/result";
import type { Customer } from "../api/types";
import { INCIDENT, vcColor } from "../lib/colors";

export type LatLon = [number, number];

export interface MapLine {
  geometry: LatLon[];
  color: string;
  weight?: number;
  dashed?: boolean;
  label?: string;
  opacity?: number;
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
}

interface Drawable {
  lines: Array<MapLine & { kind: "flow" | "route" | "extra" }>;
  customers: Customer[];
  depot: LatLon | null;
  incident: { center: LatLon; radius_m: number } | null;
  points: MapPoint[];
}

function useDrawable(p: RouteMapProps): Drawable {
  return useMemo(() => {
    const lines: Drawable["lines"] = [];
    if (p.showFlows && p.edgeFlows?.length) {
      const maxFlow = Math.max(1e-9, ...p.edgeFlows.map((e) => e.fleet_flow));
      for (const e of p.edgeFlows) {
        lines.push({
          kind: "flow",
          geometry: e.geometry,
          color: vcColor(e.vc_ratio),
          weight: 2 + (8 * e.fleet_flow) / maxFlow,
          opacity: 0.85,
          label: `flow ${e.fleet_flow} · V/C ${e.vc_ratio}`,
        });
      }
    }
    for (const r of p.routes ?? []) {
      lines.push({ kind: "route", geometry: r.geometry, color: r.color, weight: 4, label: `Vehicle ${r.vehicle}` });
    }
    for (const l of p.extraLines ?? []) lines.push({ ...l, kind: "extra" });
    const firstRoute = p.routes?.find((r) => r.geometry?.length);
    const depot = p.depot ?? (firstRoute ? firstRoute.geometry[0] : null);
    return { lines, customers: p.customers ?? [], depot, incident: p.incident ?? null, points: p.points ?? [] };
  }, [p.showFlows, p.edgeFlows, p.routes, p.extraLines, p.customers, p.depot, p.incident, p.points]);
}

function allPoints(d: Drawable): LatLon[] {
  const pts: LatLon[] = [];
  d.lines.forEach((l) => l.geometry.forEach((g) => pts.push(g)));
  d.customers.forEach((c) => pts.push([c.lat, c.lon]));
  d.points.forEach((c) => pts.push([c.lat, c.lon]));
  if (d.depot) pts.push(d.depot);
  return pts.filter((x) => Array.isArray(x) && Number.isFinite(x[0]) && Number.isFinite(x[1]));
}

const starIcon = L.divIcon({
  className: "qr-depot-icon",
  html:
    '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M12 2l2.9 6.9 7.1.6-5.4 4.7 1.7 7-6.3-3.9-6.3 3.9 1.7-7L2 9.5l7.1-.6z" fill="#0b1530" stroke="#fff" stroke-width="1.5"/></svg>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
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

function ClickHandler({ onClick }: { onClick?: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onClick?.(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// ------------------------------------------------------------------ canvas fallback

function CanvasMap({ d, plain, onMapClick }: { d: Drawable; plain: boolean; onMapClick?: (a: number, b: number) => void }) {
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
    ctx.fillStyle = "#f1f5f9";
    ctx.fillRect(0, 0, size.w, size.h);

    const pts = allPoints(d);
    if (d.incident) {
      const r = plain ? d.incident.radius_m / 1000 : d.incident.radius_m / 111320;
      pts.push([d.incident.center[0] - r, d.incident.center[1] - r], [d.incident.center[0] + r, d.incident.center[1] + r]);
    }
    if (!pts.length) {
      ctx.fillStyle = "#64748b";
      ctx.font = "13px system-ui, sans-serif";
      ctx.fillText("Nothing to draw yet", 16, 24);
      tfRef.current = null;
      return;
    }
    const lats = pts.map((p) => p[0]);
    const lons = pts.map((p) => p[1]);
    const minA = Math.min(...lats), maxA = Math.max(...lats), minB = Math.min(...lons), maxB = Math.max(...lons);
    const midA = (minA + maxA) / 2;
    const kx = plain ? 1 : Math.cos((midA * Math.PI) / 180); // squash longitude
    const spanX = Math.max(1e-9, (maxB - minB) * kx);
    const spanY = Math.max(1e-9, maxA - minA);
    const pad = 24;
    const s = Math.min((size.w - 2 * pad) / spanX, (size.h - 2 * pad) / spanY);
    const offX = (size.w - spanX * s) / 2;
    const offY = (size.h - spanY * s) / 2;
    const toXY = (p: LatLon): [number, number] => [offX + (p[1] - minB) * kx * s, size.h - offY - (p[0] - minA) * s];
    const toLL = (x: number, y: number): LatLon => [minA + (size.h - offY - y) / s, minB + (x - offX) / (kx * s)];
    tfRef.current = { toXY, toLL };

    for (const l of d.lines) {
      if (l.geometry.length < 2) continue;
      ctx.beginPath();
      l.geometry.forEach((g, i) => {
        const [x, y] = toXY(g);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = l.color;
      ctx.globalAlpha = l.opacity ?? 0.9;
      ctx.lineWidth = l.weight ?? 3;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.setLineDash(l.dashed ? [8, 6] : []);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    if (d.incident) {
      const [cx, cy] = toXY(d.incident.center);
      const r = (plain ? d.incident.radius_m / 1000 : d.incident.radius_m / 111320) * s;
      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(4, r), 0, Math.PI * 2);
      ctx.fillStyle = "rgba(220,38,38,0.2)";
      ctx.fill();
      ctx.strokeStyle = INCIDENT;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    for (const c of d.customers) {
      const [x, y] = toXY([c.lat, c.lon]);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
      ctx.strokeStyle = "#0f172a";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
    for (const p of d.points) {
      const [x, y] = toXY([p.lat, p.lon]);
      ctx.beginPath();
      ctx.arc(x, y, 7, 0, Math.PI * 2);
      ctx.fillStyle = p.color ?? "#0d9488";
      ctx.fill();
      if (p.label) {
        ctx.fillStyle = "#0f172a";
        ctx.font = "12px system-ui, sans-serif";
        ctx.fillText(p.label, x + 9, y - 9);
      }
    }
    if (d.depot) {
      const [x, y] = toXY(d.depot);
      ctx.beginPath();
      for (let i = 0; i < 10; i++) {
        const r = i % 2 === 0 ? 11 : 5;
        const a = -Math.PI / 2 + (i * Math.PI) / 5;
        const px = x + r * Math.cos(a), py = y + r * Math.sin(a);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = "#0b1530";
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }, [d, size, plain]);

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
        style={{ width: "100%", height: "100%", display: "block", cursor: onMapClick ? "crosshair" : "default" }}
      />
    </div>
  );
}

// ------------------------------------------------------------------ main component

export default function RouteMap(props: RouteMapProps) {
  const d = useDrawable(props);
  const [tilesFailed, setTilesFailed] = useState(false);
  const stats = useRef({ errors: 0, loads: 0 });
  const pts = useMemo(() => allPoints(d), [d]);
  const height = props.height ?? 480;
  const useCanvas = props.plain || tilesFailed;
  const center: LatLon = pts[0] ?? [17.4, 78.47];

  const onTileError = () => {
    stats.current.errors += 1;
    if ((stats.current.errors >= 2 && stats.current.loads === 0) || stats.current.errors >= 12) setTilesFailed(true);
  };

  return (
    <div className={`relative overflow-hidden rounded-lg border border-slate-200 bg-slate-100 ${props.className ?? ""}`} style={{ height }}>
      {useCanvas ? (
        <>
          <CanvasMap d={d} plain={!!props.plain} onMapClick={props.onMapClick} />
          <div className="absolute left-2 top-2 rounded bg-slate-800/80 px-2 py-1 text-xs text-white">
            {props.plain ? "offline map · planar coordinates (no basemap)" : "offline map · tiles unavailable"}
          </div>
        </>
      ) : (
        <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            eventHandlers={{
              tileerror: onTileError,
              tileload: () => {
                stats.current.loads += 1;
              },
            }}
          />
          <FitBounds pts={pts} />
          <ClickHandler onClick={props.onMapClick} />
          {d.lines.map((l, i) => (
            <Polyline
              key={`${l.kind}-${i}`}
              positions={l.geometry}
              pathOptions={{ color: l.color, weight: l.weight ?? 3, opacity: l.opacity ?? 0.9, dashArray: l.dashed ? "8 6" : undefined }}
            >
              {l.label && <Tooltip sticky>{l.label}</Tooltip>}
            </Polyline>
          ))}
          {d.incident && (
            <Circle center={d.incident.center} radius={d.incident.radius_m} pathOptions={{ color: INCIDENT, fillColor: INCIDENT, fillOpacity: 0.2 }} />
          )}
          {d.customers.map((c) => (
            <CircleMarker key={`c-${c.id}`} center={[c.lat, c.lon]} radius={5} pathOptions={{ color: "#0f172a", weight: 1.5, fillColor: "#fff", fillOpacity: 1 }}>
              <Tooltip>{`Customer ${c.id} · demand ${c.demand}`}</Tooltip>
            </CircleMarker>
          ))}
          {d.points.map((p, i) => (
            <CircleMarker key={`p-${i}`} center={[p.lat, p.lon]} radius={8} pathOptions={{ color: "#fff", weight: 2, fillColor: p.color ?? "#0d9488", fillOpacity: 1 }}>
              {p.label && <Tooltip permanent direction="top">{p.label}</Tooltip>}
            </CircleMarker>
          ))}
          {d.depot && (
            <Marker position={d.depot} icon={starIcon}>
              <Tooltip>Depot</Tooltip>
            </Marker>
          )}
        </MapContainer>
      )}
    </div>
  );
}
