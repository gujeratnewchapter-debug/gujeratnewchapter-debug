'use client';

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, X } from 'lucide-react';

import {
  type Advertisement,
  getAdvertisements,
  resolveMediaUrl,
  trackAdvertisementEvent,
} from '@/lib/api';

const STORAGE_PREFIX = 'ess-ad-seen-';
const APPROVED_VIDEO_HOSTS = new Set([
  'youtube.com',
  'www.youtube.com',
  'm.youtube.com',
  'youtu.be',
  'youtube-nocookie.com',
  'www.youtube-nocookie.com',
  'vimeo.com',
  'www.vimeo.com',
  'player.vimeo.com',
]);

function getEventId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function safeMediaUrl(value: string | null | undefined) {
  if (!value) return null;
  if (value.startsWith('/') && !value.startsWith('//')) return resolveMediaUrl(value);
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? url.toString() : null;
  } catch {
    return null;
  }
}

function getVideoEmbedUrl(value: string) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !APPROVED_VIDEO_HOSTS.has(url.hostname.toLowerCase())) return null;

    if (url.hostname.toLowerCase().includes('youtube') || url.hostname.toLowerCase() === 'youtu.be') {
      const videoId = url.hostname.toLowerCase() === 'youtu.be'
        ? url.pathname.split('/').filter(Boolean)[0]
        : url.searchParams.get('v') ?? url.pathname.match(/^\/(?:embed|shorts)\/([^/]+)/)?.[1];
      if (!videoId || !/^[\w-]{11}$/.test(videoId)) return null;
      return `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&autoplay=1&mute=1`;
    }

    const vimeoId = url.pathname.split('/').filter(Boolean).find((part) => /^\d+$/.test(part));
    return vimeoId ? `https://player.vimeo.com/video/${vimeoId}?autoplay=1&muted=1` : null;
  } catch {
    return null;
  }
}

function getStorage(kind: 'local' | 'session') {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
}

function readStorage(storage: Storage | null, key: string) {
  if (!storage) return null;
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(storage: Storage | null, key: string, value: string) {
  if (!storage) return false;
  try {
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function localDateKey() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function hasFrequencyMarker(advertisement: Advertisement, visitIds: Set<number>) {
  if (visitIds.has(advertisement.id)) return true;
  const key = `${STORAGE_PREFIX}${advertisement.id}`;
  if (advertisement.frequency === 'daily') {
    return readStorage(getStorage('local'), key) === localDateKey();
  }
  if (advertisement.frequency === 'session') {
    return readStorage(getStorage('session'), key) === 'shown';
  }
  return visitIds.has(advertisement.id);
}

function markFrequency(advertisement: Advertisement, visitIds: Set<number>) {
  const key = `${STORAGE_PREFIX}${advertisement.id}`;
  if (advertisement.frequency === 'daily') {
    writeStorage(getStorage('local'), key, localDateKey());
  } else if (advertisement.frequency === 'session') {
    writeStorage(getStorage('session'), key, 'shown');
  }
  visitIds.add(advertisement.id);
}

function sendEvent(advertisementId: number, eventType: 'impression' | 'click') {
  void trackAdvertisementEvent(advertisementId, eventType, getEventId()).catch((error: unknown) => {
    console.warn(`Failed to track advertisement ${eventType}:`, error);
  });
}

export function AdvertisementPopup() {
  const pathname = usePathname() || '/';
  const [advertisement, setAdvertisement] = useState<Advertisement | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState(0);
  const [videoFailed, setVideoFailed] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const dialogRef = useRef<HTMLElement>(null);
  const visitIds = useRef(new Set<number>());
  const clickedIds = useRef(new Set<number>());
  const impressedIds = useRef(new Set<number>());
  const secondsRemainingRef = useRef(secondsRemaining);

  useEffect(() => {
    secondsRemainingRef.current = secondsRemaining;
  }, [secondsRemaining]);

  useEffect(() => {
    let cancelled = false;
    let delayTimer: number | undefined;
    setAdvertisement(null);
    setVideoFailed(false);
    setImageFailed(false);

    getAdvertisements(pathname)
      .then(({ data }) => {
        if (cancelled || !Array.isArray(data)) return;
        const candidate = data.find((item) => !hasFrequencyMarker(item, visitIds.current));
        if (!candidate) return;

        delayTimer = window.setTimeout(() => {
          if (cancelled) return;
          setSecondsRemaining(Math.max(0, candidate.close_countdown_seconds));
          setAdvertisement(candidate);
        }, Math.min(60, Math.max(0, candidate.display_delay_seconds)) * 1000);
      })
      .catch((error: unknown) => {
        if (!cancelled) console.warn('Failed to load advertisements:', error);
      });

    return () => {
      cancelled = true;
      if (delayTimer) window.clearTimeout(delayTimer);
    };
  }, [pathname]);

  useEffect(() => {
    if (!advertisement || impressedIds.current.has(advertisement.id)) return;
    impressedIds.current.add(advertisement.id);
    markFrequency(advertisement, visitIds.current);
    sendEvent(advertisement.id, 'impression');
  }, [advertisement]);

  useEffect(() => {
    if (!advertisement || secondsRemaining <= 0) return undefined;
    const countdown = window.setTimeout(() => {
      setSecondsRemaining((remaining) => Math.max(0, remaining - 1));
    }, 1000);
    return () => window.clearTimeout(countdown);
  }, [advertisement, secondsRemaining]);

  useEffect(() => {
    if (!advertisement) return undefined;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && secondsRemainingRef.current === 0) {
        setAdvertisement(null);
      }
      if (event.key !== 'Tab') return;

      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) {
        event.preventDefault();
        dialogRef.current?.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      previousFocus?.focus();
    };
  }, [advertisement]);

  if (!advertisement) return null;

  const image = safeMediaUrl(advertisement.image || advertisement.image_url);
  const logo = safeMediaUrl(advertisement.advertiser_logo);
  const videoFile = safeMediaUrl(advertisement.video_file);
  const imageConfigured = Boolean(advertisement.image || advertisement.image_url);
  const videoConfigured = Boolean(advertisement.video_file || advertisement.video_url);
  const videoEmbed = !videoFile && advertisement.video_url
    ? getVideoEmbedUrl(advertisement.video_url)
    : null;
  const destination = safeMediaUrl(advertisement.destination_url);
  const videoUnavailable = videoConfigured && !videoFile && !videoEmbed;
  const imageUnavailable = imageConfigured && !image;

  function closeAdvertisement() {
    if (secondsRemaining > 0) return;
    setAdvertisement(null);
  }

  function trackClick() {
    if (!advertisement) return;
    if (clickedIds.current.has(advertisement.id)) return;
    clickedIds.current.add(advertisement.id);
    sendEvent(advertisement.id, 'click');
  }

  return (
    <div
      className="advertisement-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && secondsRemaining === 0) closeAdvertisement();
      }}
    >
      <section
        ref={dialogRef}
        className="advertisement-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="advertisement-headline"
        tabIndex={-1}
      >
        <div className="advertisement-toolbar">
          <span className="advertisement-label">Advertisement</span>
          <button
            className="advertisement-close"
            type="button"
            disabled={secondsRemaining > 0}
            onClick={closeAdvertisement}
            aria-label={secondsRemaining > 0 ? `Close advertisement in ${secondsRemaining} seconds` : 'Close advertisement'}
          >
            {secondsRemaining > 0
              ? <span aria-live="polite">Close in {secondsRemaining}s</span>
              : <X size={20} aria-hidden="true" />}
          </button>
        </div>

        {videoFile && !videoFailed && (
          <video
            className="advertisement-video"
            autoPlay
            controls
            muted
            preload="metadata"
            playsInline
            onError={() => setVideoFailed(true)}
            aria-label={advertisement.headline || `Video advertisement from ${advertisement.advertiser_name || 'sponsor'}`}
          >
            <source src={videoFile} />
            Your browser could not play this advertisement.
          </video>
        )}
        {videoEmbed && !videoFailed && (
          <div className="advertisement-video-frame">
            <iframe
              src={videoEmbed}
              title={advertisement.headline || `Video advertisement from ${advertisement.advertiser_name || 'sponsor'}`}
              allow="autoplay; encrypted-media; picture-in-picture"
              allowFullScreen
              onError={() => setVideoFailed(true)}
            />
          </div>
        )}
        {(videoUnavailable || (advertisement.content_type === 'video' && !videoConfigured)) && (
          <p className="advertisement-fallback">This video advertisement is unavailable.</p>
        )}
        {videoFailed && <p className="advertisement-fallback">This video advertisement is unavailable.</p>}

        {image && !imageFailed && (
          <Image
            className="advertisement-image"
            src={image}
            alt={advertisement.image_alt_text || advertisement.advertiser_name || 'Sponsored promotion'}
            width={1200}
            height={675}
            unoptimized
            loading="lazy"
            decoding="async"
            onError={() => setImageFailed(true)}
          />
        )}
        {(imageFailed || imageUnavailable || (advertisement.content_type === 'image' && !imageConfigured)) && (
          <p className="advertisement-fallback">This image advertisement is unavailable.</p>
        )}

        <div className="advertisement-copy">
          {logo && (
            <Image
              className="advertisement-logo"
              src={logo}
              alt={advertisement.advertiser_name ? `${advertisement.advertiser_name} logo` : 'Advertiser logo'}
              width={300}
              height={128}
              unoptimized
              loading="lazy"
              decoding="async"
              onError={(event) => {
                event.currentTarget.hidden = true;
              }}
            />
          )}
          {advertisement.advertiser_name && <p className="advertisement-sponsor">{advertisement.advertiser_name}</p>}
          {advertisement.headline && <h2 id="advertisement-headline">{advertisement.headline}</h2>}
          {!advertisement.headline && <h2 id="advertisement-headline" className="sr-only">Sponsored advertisement</h2>}
          {advertisement.description && <p>{advertisement.description}</p>}
          {advertisement.promotional_text && <p className="advertisement-offer">{advertisement.promotional_text}</p>}
          {destination && advertisement.cta_label && (
            <a
              className="btn btn-primary advertisement-cta"
              href={destination}
              target="_blank"
              rel="noopener noreferrer"
              onClick={trackClick}
            >
              {advertisement.cta_label}
              <ArrowUpRight size={16} aria-hidden="true" />
            </a>
          )}
        </div>
      </section>
    </div>
  );
}
