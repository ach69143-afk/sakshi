import React, { useState, useEffect } from 'react';
import { useMap, Circle, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { 
  Clock, 
  MapPin, 
  Radio, 
  PhoneCall, 
  AlertTriangle, 
  FileText
} from 'lucide-react';
import { getGoldenHourApi } from '../api';
import { useAuth } from '../context/AuthContext';
import EvidenceModal from '../components/EvidenceModal';
import MapBackdrop from '../components/MapBackdrop';

// Red dot marker with name label
const createMissingPin = (id, name) => L.divIcon({
  className: 'custom-leaflet-marker',
  html: `
    <div style="position: relative; display: flex; flex-direction: column; align-items: center; cursor: pointer;">
      <div style="width: 14px; height: 14px; border-radius: 50%; background: #ef2b2d; border: 2px solid #ffffff; box-shadow: 0 0 12px rgba(239, 43, 45, 0.9);"></div>
      <div style="background: rgba(14, 16, 19, 0.95); border: 1px solid #2b1416; border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: 700; color: #ffffff; white-space: nowrap; margin-top: 3px; font-family: monospace; box-shadow: 0 2px 6px rgba(0,0,0,0.7);">
        ${name.split(' ')[0]}
      </div>
    </div>
  `,
  iconSize: [40, 32],
  iconAnchor: [20, 7]
});

// Centroid marker
const centroidPin = L.divIcon({
  className: 'custom-centroid-marker',
  html: `
    <div style="width: 16px; height: 16px; border-radius: 50%; background: #ef2b2d; border: 2.5px solid #ffffff; box-shadow: 0 0 16px #ef2b2d;"></div>
  `,
  iconSize: [16, 16],
  iconAnchor: [8, 8]
});

// Helper component to fit map bounds to the missing person pins
const BoundsFitter = ({ points }) => {
  const map = useMap();
  useEffect(() => {
    if (points && points.length > 0) {
      const bounds = L.latLngBounds(points.map(p => [p.lat, p.lon]));
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });
    }
  }, [points, map]);
  return null;
};

export const GoldenHour = () => {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [selectedEvidence, setSelectedEvidence] = useState(null);

  useEffect(() => {
    const fetchGH = async () => {
      try {
        const gh = await getGoldenHourApi();
        setData(gh);
      } catch (err) {
        console.error("Golden Hour data load error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchGH();
  }, [user?.role]);

  const centroid = data?.centroid || [21.21834, 81.34172];

  return (
    <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden bg-slate-950">
      {/* Evidence Modal */}
      <EvidenceModal evidenceId={selectedEvidence} onClose={() => setSelectedEvidence(null)} />

      {/* Map View Canvas with MapBackdrop */}
      <div className="flex-1 h-[55vh] lg:h-full relative overflow-hidden">
        <MapBackdrop
          center={centroid}
          zoom={13}
          interactive={true}
          className="h-full w-full"
        >
          {data?.missing && <BoundsFitter points={data.missing} />}

          {/* Centroid Civic Center */}
          <Marker position={centroid} icon={centroidPin}>
            <Popup>
              <div className="text-xs p-1">
                <div className="font-bold text-red-400 font-heading">Centroid Area of Interest</div>
                <div className="text-[11px] text-slate-300 font-mono">
                  {centroid[0].toFixed(4)}° N, {centroid[1].toFixed(4)}° E
                </div>
              </div>
            </Popup>
          </Marker>

          {/* Dashed red 3 km circle with CSS pulse animation and soft red radial glow */}
          <Circle
            center={centroid}
            radius={3000}
            pathOptions={{
              color: '#ef2b2d',
              fillColor: '#ef2b2d',
              fillOpacity: 0.15,
              weight: 2,
              dashArray: '6, 6',
              className: 'pulsing-circle'
            }}
          />

          {/* Missing Person Pins (Red dots with labels) */}
          {data?.missing?.map((p) => (
            <Marker
              key={p.id}
              position={[p.lat, p.lon]}
              icon={createMissingPin(p.id, p.name)}
              eventHandlers={{
                click: () => setSelectedPerson(p)
              }}
            >
              <Popup>
                <div className="text-xs p-1 space-y-1">
                  <div className="font-mono text-red-400 font-bold">{p.id}</div>
                  <div className="font-bold text-slate-100">{p.name} (Age {p.age})</div>
                  <div className="text-[11px] text-slate-300">Last seen: {new Date(p.last_seen_time).toLocaleString()}</div>
                  <div className="text-[10px] text-slate-400">{p.landmark}</div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapBackdrop>

        {/* Small single map legend */}
        <div className="absolute top-4 left-4 bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-2xl backdrop-blur-md z-[1000] text-xs space-y-1.5 pointer-events-auto">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></span>
            <span className="font-bold text-slate-100 uppercase tracking-wider font-heading">
              Golden Hour Departure Zone (3 km)
            </span>
          </div>
          <div className="text-[10px] text-slate-400 font-mono">
            Centroid: {centroid[0].toFixed(4)}° N, {centroid[1].toFixed(4)}° E • NH-53 Corridor
          </div>
        </div>
      </div>

      {/* Right Intelligence Dossier Sidebar (Red theme, doesn't cover centroid) */}
      <div className="w-full lg:w-96 bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 p-5 overflow-y-auto space-y-5 flex-shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 text-xs font-mono font-bold bg-red-950 text-red-300 border border-red-800 rounded flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-red-400" />
              24-HR GOLDEN HOUR CORRELATION
            </span>
          </div>
          <h2 className="text-lg font-bold text-slate-100 font-heading">Spatio-Temporal Analysis</h2>
          <p className="text-xs text-slate-400 mt-1">
            Cross-referencing missing individual timelines against proximate mobile telemetry and highway exit corridors.
          </p>
        </div>

        {/* Burner Device Card (Red Theme) */}
        {data?.burner && (
          <div className="p-4 rounded-xl bg-slate-950 border border-red-900/60 space-y-2.5 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-red-400" />
                <span className="font-bold text-xs text-red-300 uppercase tracking-wide font-heading">
                  Proximity Burner Identifier
                </span>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-mono bg-red-950 text-red-300 rounded border border-red-800 font-bold">
                HIGH PRIORITY
              </span>
            </div>

            <div className="font-mono text-sm font-bold text-slate-100 bg-slate-900 p-2.5 rounded border border-slate-800 flex items-center justify-between">
              <span>{data.burner.number}</span>
              <span className="text-[10px] text-red-400 uppercase tracking-wider font-semibold">Toll Passage</span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              {data.burner.notes}
            </p>

            <div className="pt-1 flex items-center justify-between text-[11px] font-mono text-slate-400 border-t border-slate-800/80">
              <span>Corridor Exit:</span>
              <span className="text-slate-200">{data.burner.last_seen_toll}</span>
            </div>
          </div>
        )}

        {/* Bait Ad Card (Red Theme) */}
        {data?.bait && (
          <div className="p-4 rounded-xl bg-slate-950 border border-red-900/60 space-y-2.5 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PhoneCall className="w-4 h-4 text-red-400" />
                <span className="font-bold text-xs text-red-300 uppercase tracking-wide font-heading">
                  Digital Bait Contact
                </span>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-mono bg-red-950 text-red-300 rounded border border-red-800 font-bold">
                {data.bait.contacted_by} / 5 CONTACTS
              </span>
            </div>

            <div className="font-mono text-sm font-bold text-slate-100 bg-slate-900 p-2.5 rounded border border-slate-800 flex items-center justify-between">
              <span>{data.bait.number}</span>
              <span className="text-[10px] text-red-400 font-semibold">Ad Campaign</span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed italic">
              "{data.bait.ad_campaign}"
            </p>

            <p className="text-xs text-slate-400 leading-relaxed">
              {data.bait.notes}
            </p>
          </div>
        )}

        {/* Missing Individuals Summary Table */}
        <div className="space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-heading">
            Missing Individuals Cluster ({data?.missing?.length || 0})
          </div>
          <div className="space-y-1.5">
            {data?.missing?.map(p => (
              <div 
                key={p.id}
                onClick={() => setSelectedPerson(p)}
                className={`p-2.5 rounded-lg border text-xs cursor-pointer transition ${
                  selectedPerson?.id === p.id 
                    ? 'bg-red-950/40 border-red-500/80 text-white' 
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between font-mono">
                  <span className="font-bold text-red-400">{p.id}</span>
                  <span className="text-[10px] text-slate-500">{new Date(p.last_seen_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <div className="font-semibold text-slate-100 mt-0.5">{p.name} (Age {p.age})</div>
                <div className="text-[11px] text-slate-400 truncate mt-0.5">{p.landmark}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GoldenHour;
