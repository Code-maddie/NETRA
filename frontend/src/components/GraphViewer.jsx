import React, { useRef, useEffect, useState, useCallback } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

export default function GraphViewer({
  topologyData,
  sourceNode,
  destNode,
  activePath = [],
  onSelectNode,
  onSelectLink,
  selectedNode,
  selectedLink
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Transform state (Pan and Zoom)
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 0.85 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState(null);

  const nodes = topologyData?.nodes || [];
  const links = topologyData?.links || [];
  const nodeCount = nodes.length;

  // Active path set and lookup for fast rendering
  const activePathSet = new Set(activePath);
  const pathEdgeSet = new Set();
  for (let i = 0; i < activePath.length - 1; i++) {
    const u = activePath[i];
    const v = activePath[i + 1];
    pathEdgeSet.add(`${Math.min(u, v)}-${Math.max(u, v)}`);
  }

  // Auto-fit graph to canvas when topology changes
  const resetView = useCallback(() => {
    if (!canvasRef.current || nodes.length === 0) return;
    const canvas = canvasRef.current;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    // Graph logical coordinates are within [50, 950]
    const scale = Math.min(width / 1100, height / 1100) * 0.95;
    const x = (width - 1000 * scale) / 2;
    const y = (height - 1000 * scale) / 2;
    setTransform({ x, y, scale: Math.max(0.15, scale) });
  }, [nodes.length]);

  useEffect(() => {
    resetView();
  }, [resetView]);

  // Handle Zoom In / Out
  const handleZoom = (factor) => {
    setTransform(prev => {
      const newScale = Math.max(0.1, Math.min(6.0, prev.scale * factor));
      if (!canvasRef.current) return prev;
      const w = canvasRef.current.clientWidth / 2;
      const h = canvasRef.current.clientHeight / 2;
      const newX = w - (w - prev.x) * (newScale / prev.scale);
      const newY = h - (h - prev.y) * (newScale / prev.scale);
      return { x: newX, y: newY, scale: newScale };
    });
  };

  // Mouse pan and zoom event handlers
  const handleWheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    setTransform(prev => {
      const newScale = Math.max(0.1, Math.min(6.0, prev.scale * factor));
      const newX = mouseX - (mouseX - prev.x) * (newScale / prev.scale);
      const newY = mouseY - (mouseY - prev.y) * (newScale / prev.scale);
      return { x: newX, y: newY, scale: newScale };
    });
  };

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setTransform(prev => ({
        ...prev,
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      }));
      return;
    }

    // Hover detection for nodes
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - transform.x) / transform.scale;
    const mouseY = (e.clientY - rect.top - transform.y) / transform.scale;

    const hitRadius = Math.max(6, 12 / transform.scale);
    let hit = null;

    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const dx = n.x - mouseX;
      const dy = n.y - mouseY;
      if (dx * dx + dy * dy < hitRadius * hitRadius) {
        hit = n;
        break;
      }
    }
    setHoveredNode(hit);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleClick = (e) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - transform.x) / transform.scale;
    const mouseY = (e.clientY - rect.top - transform.y) / transform.scale;

    // Check node click
    const nodeHitRadius = Math.max(7, 14 / transform.scale);
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const dx = n.x - mouseX;
      const dy = n.y - mouseY;
      if (dx * dx + dy * dy < nodeHitRadius * nodeHitRadius) {
        if (onSelectNode) onSelectNode(n);
        return;
      }
    }

    // Check link click (distance to line segment)
    const linkHitDist = Math.max(5, 8 / transform.scale);
    for (let i = 0; i < links.length; i++) {
      const l = links[i];
      const u = nodes.find(n => n.id === l.source);
      const v = nodes.find(n => n.id === l.target);
      if (!u || !v) continue;

      const dist = distanceToSegment(mouseX, mouseY, u.x, u.y, v.x, v.y);
      if (dist < linkHitDist) {
        if (onSelectLink) onSelectLink(l);
        return;
      }
    }
  };

  function distanceToSegment(px, py, x1, y1, x2, y2) {
    const l2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
    if (l2 === 0) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)));
  }

  // Animation frame loop for rendering Canvas
  useEffect(() => {
    let animId;
    let pulseProgress = 0;

    const render = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dpr = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;

      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      // Background subtle grid in warm neutral
      ctx.save();
      ctx.strokeStyle = 'rgba(50, 50, 50, 0.04)';
      ctx.lineWidth = 1;
      const gridSize = 40 * transform.scale;
      const offsetX = transform.x % gridSize;
      const offsetY = transform.y % gridSize;
      for (let x = offsetX; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = offsetY; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      ctx.restore();

      // Apply transform for graph elements
      ctx.save();
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.scale, transform.scale);

      // Node lookup for fast edge coordinates
      const nodeMap = new Map();
      for (let i = 0; i < nodes.length; i++) {
        nodeMap.set(nodes[i].id, nodes[i]);
      }

      // 1. Draw Links
      pulseProgress = (pulseProgress + 0.012) % 1.0;

      for (let i = 0; i < links.length; i++) {
        const link = links[i];
        const u = nodeMap.get(link.source);
        const v = nodeMap.get(link.target);
        if (!u || !v) continue;

        const isFailed = link.status === 'failed';
        const linkKey = `${Math.min(link.source, link.target)}-${Math.max(link.source, link.target)}`;
        const isOnActivePath = pathEdgeSet.has(linkKey);
        const isCongested = (link.utilization || 0) >= 0.8;
        const isSelected = selectedLink && selectedLink.id === link.id;

        ctx.beginPath();
        ctx.moveTo(u.x, u.y);
        ctx.lineTo(v.x, v.y);

        if (isFailed) {
          // Failed link: dashed red line with cross-out
          ctx.strokeStyle = '#9F3A38';
          ctx.lineWidth = 2.0;
          ctx.setLineDash([6, 5]);
          ctx.stroke();
          ctx.setLineDash([]);

          // Draw "X" fault marker at midpoint
          const midX = (u.x + v.x) / 2;
          const midY = (u.y + v.y) / 2;
          ctx.strokeStyle = '#9F3A38';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(midX - 4, midY - 4);
          ctx.lineTo(midX + 4, midY + 4);
          ctx.moveTo(midX + 4, midY - 4);
          ctx.lineTo(midX - 4, midY + 4);
          ctx.stroke();

        } else if (isOnActivePath) {
          // Active routing path: solid warm terracotta (restrained, no neon glow)
          ctx.strokeStyle = '#8A5C45';
          ctx.lineWidth = Math.max(3.0, 4.0);
          ctx.stroke();

          // Simulated packet pulse dot flowing along path
          const pulseX = u.x + (v.x - u.x) * pulseProgress;
          const pulseY = u.y + (v.y - u.y) * pulseProgress;
          ctx.fillStyle = '#FFFFFF';
          ctx.beginPath();
          ctx.arc(pulseX, pulseY, 3.5, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#8A5C45';
          ctx.lineWidth = 1.5;
          ctx.stroke();

        } else if (isSelected) {
          ctx.strokeStyle = '#526B73';
          ctx.lineWidth = 3.0;
          ctx.stroke();

        } else if (isCongested) {
          // Congested link: restrained amber
          ctx.strokeStyle = '#A96B1E';
          ctx.lineWidth = 2.2;
          ctx.stroke();

        } else {
          // Normal link in subtle blue-grey
          const util = link.utilization || 0.1;
          const alpha = Math.min(0.5, Math.max(0.18, 0.7 - nodeCount / 1200));
          ctx.strokeStyle = util > 0.5 ? 'rgba(169, 107, 30, 0.45)' : `rgba(82, 107, 115, ${alpha})`;
          ctx.lineWidth = nodeCount > 500 ? 0.75 : 1.2;
          ctx.stroke();
        }
      }

      // 2. Draw Nodes
      const baseNodeRadius = nodeCount > 500 ? 3 : (nodeCount > 200 ? 4.5 : (nodeCount > 50 ? 6 : 9));
      const shouldDrawLabels = nodeCount <= 50 || transform.scale >= 1.6;

      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        const isSource = n.id === sourceNode;
        const isDest = n.id === destNode;
        const isInPath = activePathSet.has(n.id);
        const isHovered = hoveredNode && hoveredNode.id === n.id;
        const isSelected = selectedNode && selectedNode.id === n.id;

        let radius = baseNodeRadius;
        let fillColor = '#526B73'; // Muted blue-grey
        let strokeColor = '#F5EFEB'; // Warm off-white
        let strokeWidth = 1.5;

        if (isSource) {
          radius = baseNodeRadius + 4;
          fillColor = '#2E7D52'; // Restrained green
          strokeColor = '#F5EFEB';
          strokeWidth = 2.5;
        } else if (isDest) {
          radius = baseNodeRadius + 4;
          fillColor = '#8A5C45'; // Muted terracotta
          strokeColor = '#F5EFEB';
          strokeWidth = 2.5;
        } else if (isSelected) {
          radius = baseNodeRadius + 3;
          fillColor = '#323232'; // Dark grey
          strokeColor = '#8A5C45'; // Terracotta accent ring
          strokeWidth = 2.5;
        } else if (isInPath) {
          radius = baseNodeRadius + 2;
          fillColor = '#8A5C45';
          strokeColor = '#F5EFEB';
          strokeWidth = 2.0;
        } else if (isHovered) {
          radius = baseNodeRadius + 2;
          fillColor = '#43585F';
          strokeColor = '#323232';
          strokeWidth = 2.0;
        }

        ctx.beginPath();
        ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.lineWidth = strokeWidth;
        ctx.strokeStyle = strokeColor;
        ctx.stroke();

        // Draw node labels selectively
        if (shouldDrawLabels || isSource || isDest || isSelected || isHovered) {
          ctx.font = `${isSource || isDest ? 'bold 12px' : '10px'} Inter, -apple-system, sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = isSource ? '#2E7D52' : (isDest ? '#8A5C45' : (isInPath ? '#8A5C45' : '#323232'));
          
          let labelText = `${n.id}`;
          if (isSource) labelText = `SRC: ${n.id}`;
          if (isDest) labelText = `DST: ${n.id}`;
          
          ctx.fillText(labelText, n.x, n.y - radius - 8);
        }
      }

      ctx.restore();
      ctx.restore();

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [nodes, links, transform, sourceNode, destNode, activePath, hoveredNode, selectedNode, selectedLink, nodeCount]);

  return (
    <div className="graph-viewport-container" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className="graph-canvas"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onClick={handleClick}
        aria-label="Interactive graph canvas showing nodes, links, and simulated packet flow"
      />

      {/* Graph Control Overlay */}
      <div className="graph-overlay-controls" aria-label="Graph Zoom and Fit Controls">
        <button
          type="button"
          className="graph-tool-btn"
          onClick={() => handleZoom(1.25)}
          title="Zoom In"
          aria-label="Zoom in"
        >
          <ZoomIn size={16} />
        </button>
        <button
          type="button"
          className="graph-tool-btn"
          onClick={() => handleZoom(0.8)}
          title="Zoom Out"
          aria-label="Zoom out"
        >
          <ZoomOut size={16} />
        </button>
        <button
          type="button"
          className="graph-tool-btn"
          onClick={resetView}
          title="Reset View / Fit to Window"
          aria-label="Reset view"
        >
          <Maximize2 size={16} />
        </button>
      </div>

      {/* Visual Legend */}
      <div className="graph-legend" aria-label="Graph Legend">
        <div className="legend-item">
          <span className="legend-indicator" style={{ background: '#2E7D52' }} />
          <span>Source</span>
        </div>
        <div className="legend-item">
          <span className="legend-indicator" style={{ background: '#8A5C45' }} />
          <span>Destination</span>
        </div>
        <div className="legend-item">
          <span className="legend-line" style={{ background: '#8A5C45' }} />
          <span>Active Route</span>
        </div>
        <div className="legend-item">
          <span className="legend-line" style={{ background: '#A96B1E' }} />
          <span>Congested (&ge;80%)</span>
        </div>
        <div className="legend-item">
          <span className="legend-line legend-line-dashed" style={{ borderColor: '#9F3A38' }} />
          <span>Link Fault</span>
        </div>
      </div>
    </div>
  );
}
