import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

export const MapBackdrop = ({
  center = [21.21834, 81.34172],
  zoom = 13,
  interactive = true,
  className = "w-full h-full",
  children
}) => {
  const mapRef = useRef(null);

  return (
    <div className={`relative overflow-hidden ${className}`} style={{
      backgroundImage: `
        repeating-linear-gradient(0deg, rgba(239, 43, 45, 0.04) 0px, rgba(239, 43, 45, 0.04) 1px, transparent 1px, transparent 24px),
        repeating-linear-gradient(90deg, rgba(239, 43, 45, 0.04) 0px, rgba(239, 43, 45, 0.04) 1px, transparent 1px, transparent 24px),
        radial-gradient(ellipse at center, rgba(14, 16, 19, 0.6) 0%, rgba(7, 8, 10, 0.95) 100%)
      `,
      backgroundColor: '#07080a'
    }}>
      <MapContainer
        center={center}
        zoom={zoom}
        dragging={interactive}
        zoomControl={interactive}
        scrollWheelZoom={interactive}
        doubleClickZoom={interactive}
        touchZoom={interactive}
        attributionControl={false}
        className="w-full h-full z-0"
        ref={mapRef}
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="map-backdrop-tiles"
          maxZoom={19}
        />
        {children}
      </MapContainer>
    </div>
  );
};

export default MapBackdrop;
