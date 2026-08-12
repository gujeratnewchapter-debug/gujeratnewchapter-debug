"use client";

import React, { useEffect, useRef } from "react";
import gsap from "gsap";
import "./cursor-image-trail.css";

const ASSET_PATHS = [
  "/images/cursor-trail/curser1.jpg",
  "/images/cursor-trail/curser2.jpg",
  "/images/cursor-trail/curser3.jpg",
  "/images/cursor-trail/curser4.jpg",
  "/images/cursor-trail/curser5.jpg",
  "/images/cursor-trail/curser6.jpg",
  "/images/cursor-trail/curser7.jpg",
  "/images/cursor-trail/curser8.jpg",
  "/images/cursor-trail/curser9.jpg",
  "/images/cursor-trail/curser10.jpg",
  "/images/cursor-trail/curser11.png",
  "/images/cursor-trail/curser12.png",
];

export function CursorImageTrail() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const poolRef = useRef<HTMLDivElement[]>([]);
  const lastSpawnRef = useRef(0);
  const lastPosRef = useRef({ x: 0, y: 0 });
  const enabledRef = useRef(false);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Respect reduced motion and pointer capabilities
    const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!canHover || reduceMotion) return;
    enabledRef.current = true;

    const container = containerRef.current!;
    // Create a fixed pool of elements
    const POOL_SIZE = 8;
    for (let i = 0; i < POOL_SIZE; i++) {
      const el = document.createElement("div");
      el.className = "cursor-trail-item";
      el.setAttribute("aria-hidden", "true");
      const img = document.createElement("img");
      img.className = "cursor-trail-img";
      img.draggable = false;
      el.appendChild(img);
      container.appendChild(el);
      poolRef.current.push(el);
    }

    // Preload assets
    ASSET_PATHS.forEach((p) => {
      const img = new Image();
      img.src = p;
    });

    function getDistance(a: any, b: any) {
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      return Math.sqrt(dx * dx + dy * dy);
    }

    function spawnAt(x: number, y: number, velocity = 0) {
      const now = performance.now();
      const MIN_INTERVAL = 120; // ms
      if (now - lastSpawnRef.current < MIN_INTERVAL) return;
      lastSpawnRef.current = now;

      // pick an available element
      const item = poolRef.current.shift();
      if (!item) return;

      const img = item.querySelector("img")! as HTMLImageElement;
      // choose random asset
      const asset = ASSET_PATHS[Math.floor(Math.random() * ASSET_PATHS.length)];
      img.src = asset;

      // random properties
      const rot = (Math.random() * 24 - 12).toFixed(2);
      const scale = 0.9 + Math.random() * 0.5; // 0.9 - 1.4
      const offsetX = Math.round((Math.random() - 0.5) * 36);
      const offsetY = Math.round((Math.random() - 0.5) * 36);

      // ensure visible in viewport (basic clamp)
      const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
      const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
      const clampedX = Math.min(Math.max(8, x + offsetX), vw - 8);
      const clampedY = Math.min(Math.max(8, y + offsetY), vh - 8);

      // position
      gsap.killTweensOf(item);
      gsap.set(item, {
        x: clampedX,
        y: clampedY,
        scale: 0.65,
        opacity: 0,
        rotation: rot,
        translateX: '-50%',
        translateY: '-50%',
        pointerEvents: 'none',
      });

      // animate in then out
      const tl = gsap.timeline({
        onComplete: () => {
          // recycle
          poolRef.current.push(item);
        },
      });

      tl.to(item, { opacity: 1, scale: scale, duration: 0.38, ease: 'power3.out' })
        .to(item, {
          duration: 1.0 + Math.random() * 0.6,
          x: clampedX + (Math.random() - 0.5) * 80,
          y: clampedY + (Math.random() - 0.5) * 80,
          rotation: `+=${(Math.random() - 0.5) * 12}`,
          scale: scale * 0.85,
          opacity: 0,
          ease: 'power1.out',
        }, '+=0.05');
    }

    let mouse = { x: 0, y: 0 };
    function onMove(e: MouseEvent) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      // spawn based on distance
      const dist = getDistance(mouse, lastPosRef.current);
      const speedFactor = Math.min(1.0, dist / 80);
      if (dist > 60 || Math.random() < speedFactor * 0.4) {
        spawnAt(mouse.x, mouse.y, dist);
        lastPosRef.current = { x: mouse.x, y: mouse.y };
      }
    }

    function onLeave() {
      // nothing special
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mouseout", onLeave);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseout", onLeave);
      // kill timelines and remove elements
      poolRef.current.forEach((el) => gsap.killTweensOf(el));
      if (container) container.innerHTML = "";
      enabledRef.current = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return <div ref={containerRef} className="cursor-image-trail" aria-hidden="true" />;
}

export default CursorImageTrail;
