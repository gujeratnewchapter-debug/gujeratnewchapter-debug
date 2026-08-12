'use client';

import { useEffect, useRef } from 'react';

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

interface Particle {
  x: number;
  y: number;
  radius: number;
  vx: number;
  vy: number;
  color: string;
  alpha: number;
}

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

interface Stream {
  path: Array<{ x: number; y: number }>;
  progress: number;
  speed: number;
}

interface TechVisualsProps {
  className?: string;
}

export function TechVisuals({ className = 'tech-visuals' }: TechVisualsProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointerRef = useRef({ x: 0, y: 0, active: false });
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isMobile = window.innerWidth < 800;
    const particleCount = isMobile ? 18 : 26;
    const nodeCount = isMobile ? 5 : 8;
    const streamCount = isMobile ? 2 : 3;

    let width = 0;
    let height = 0;
    const particles: Particle[] = [];
    const nodes: Node[] = [];
    const streams: Stream[] = [];
    let time = 0;

    const colors = ['rgba(16,185,129,0.28)', 'rgba(52,211,153,0.18)', 'rgba(15,118,110,0.22)'];

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const initParticles = () => {
      particles.length = 0;
      for (let i = 0; i < particleCount; i += 1) {
        const radius = Math.random() * 1.6 + 0.8;
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          radius,
          vx: (Math.random() - 0.5) * 0.08,
          vy: (Math.random() - 0.5) * 0.08,
          color: colors[i % colors.length],
          alpha: 0.12 + Math.random() * 0.1,
        });
      }
    };

    const initNodes = () => {
      nodes.length = 0;
      for (let i = 0; i < nodeCount; i += 1) {
        nodes.push({
          x: width * (0.15 + (i / nodeCount) * 0.62) + (Math.random() - 0.5) * 80,
          y: height * (0.18 + (i % 2) * 0.2) + (Math.random() - 0.5) * 60,
          vx: (Math.random() - 0.5) * 0.08,
          vy: (Math.random() - 0.5) * 0.06,
          radius: isMobile ? 3 : 4.5,
        });
      }
    };

    const initStreams = () => {
      streams.length = 0;
      for (let i = 0; i < streamCount; i += 1) {
        const start = { x: width * 0.05, y: height * (0.22 + i * 0.22) };
        const mid = { x: width * 0.35, y: height * (0.18 + i * 0.22) - 18 };
        const end = { x: width * 0.9, y: height * (0.24 + i * 0.22) + 22 };
        streams.push({
          path: [start, mid, end],
          progress: Math.random(),
          speed: 0.00025 + i * 0.00006,
        });
      }
    };

    const updateNodes = () => {
      nodes.forEach((node) => {
        if (pointerRef.current.active) {
          const dx = pointerRef.current.x - node.x;
          const dy = pointerRef.current.y - node.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 240) {
            node.vx += (dx / dist) * 0.0012;
            node.vy += (dy / dist) * 0.0012;
          }
        }
        node.x += node.vx;
        node.y += node.vy;
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;
        node.x = clamp(node.x, 0, width);
        node.y = clamp(node.y, 0, height);
      });
    };

    const drawGrid = () => {
      ctx.save();
      ctx.strokeStyle = 'rgba(16,118,110,0.08)';
      ctx.lineWidth = 1;
      const gridSize = 38;
      const offset = (time * 0.03) % gridSize;
      for (let x = -gridSize; x <= width + gridSize; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x + offset, 0);
        ctx.lineTo(x + offset, height);
        ctx.stroke();
      }
      for (let y = -gridSize; y <= height + gridSize; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y + offset);
        ctx.lineTo(width, y + offset);
        ctx.stroke();
      }
      ctx.restore();
    };

    const drawStreams = () => {
      streams.forEach((stream, index) => {
        ctx.save();
        ctx.strokeStyle = 'rgba(16,185,129,0.14)';
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(stream.path[0].x, stream.path[0].y);
        ctx.quadraticCurveTo(stream.path[1].x, stream.path[1].y, stream.path[2].x, stream.path[2].y);
        ctx.stroke();
        const t = (stream.progress * 0.9 + 0.05) % 1;
        const px = (1 - t) * (1 - t) * stream.path[0].x + 2 * (1 - t) * t * stream.path[1].x + t * t * stream.path[2].x;
        const py = (1 - t) * (1 - t) * stream.path[0].y + 2 * (1 - t) * t * stream.path[1].y + t * t * stream.path[2].y;
        ctx.fillStyle = 'rgba(52,211,153,0.7)';
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });
    };

    const drawNodes = () => {
      ctx.save();
      for (let i = 0; i < nodes.length; i += 1) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j += 1) {
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            const alpha = ((120 - dist) / 120) * 0.18;
            ctx.strokeStyle = `rgba(52,211,153,${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
      nodes.forEach((node, index) => {
        const glow = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, node.radius * 6);
        glow.addColorStop(0, 'rgba(16,185,129,0.22)');
        glow.addColorStop(1, 'rgba(16,185,129,0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    };

    const drawParticles = () => {
      ctx.save();
      particles.forEach((particle) => {
        particle.x += particle.vx;
        particle.y += particle.vy;
        if (particle.x < 0 || particle.x > width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > height) particle.vy *= -1;
        particle.x = clamp(particle.x, 0, width);
        particle.y = clamp(particle.y, 0, height);
        ctx.fillStyle = particle.color;
        ctx.globalAlpha = particle.alpha;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    };

    const render = () => {
      if (reduced) {
        ctx.clearRect(0, 0, width, height);
        drawGrid();
        drawParticles();
        return;
      }
      time += 0.25;
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = 'source-over';
      drawGrid();
      drawStreams();
      updateNodes();
      drawNodes();
      drawParticles();
      frameRef.current = window.requestAnimationFrame(render);
    };

    const handleMove = (event: MouseEvent) => {
      pointerRef.current.active = true;
      pointerRef.current.x = event.clientX;
      pointerRef.current.y = event.clientY;
    };
    const handleLeave = () => { pointerRef.current.active = false; };

    resize();
    initParticles();
    initNodes();
    initStreams();
    render();
    window.addEventListener('resize', () => {
      resize();
      initParticles();
      initNodes();
      initStreams();
    });
    canvas.addEventListener('mousemove', handleMove);
    canvas.addEventListener('mouseleave', handleLeave);

    return () => {
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
      window.removeEventListener('resize', resize);
      canvas.removeEventListener('mousemove', handleMove);
      canvas.removeEventListener('mouseleave', handleLeave);
    };
  }, []);

  return (
    <div className={className}>
      <canvas ref={canvasRef} aria-hidden="true" />
    </div>
  );
}
