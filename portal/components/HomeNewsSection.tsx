'use client';

import { useCallback, useEffect, useRef, useState, type FocusEvent } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Pause, Play } from 'lucide-react';
import { A11y, Autoplay, Keyboard } from 'swiper/modules';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperInstance } from 'swiper';
import 'swiper/css';

import { getFeaturedNews, type NewsArticle } from '@/lib/api';
import { NewsArticleCard } from '@/components/NewsArticleCard';

type NavigationState = { previous: boolean; next: boolean };

function getNavigationState(swiper: SwiperInstance): NavigationState {
  const visibleSlides = Number(swiper.params.slidesPerView);
  const canMove = swiper.slides.length > visibleSlides;
  if (!canMove) return { previous: false, next: false };
  if (swiper.params.loop || swiper.params.rewind) return { previous: true, next: true };
  return { previous: !swiper.isBeginning, next: !swiper.isEnd };
}

export function HomeNewsSection() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [swiper, setSwiper] = useState<SwiperInstance | null>(null);
  const [navigation, setNavigation] = useState<NavigationState>({ previous: false, next: false });
  const [activeIndex, setActiveIndex] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(true);
  const [motionPreferenceReady, setMotionPreferenceReady] = useState(false);
  const [userPaused, setUserPaused] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const carouselRegion = useRef<HTMLDivElement>(null);
  const pointerInside = useRef(false);
  const mouseInside = useRef(false);
  const focusInside = useRef(false);
  const userPausedRef = useRef(false);
  const announceNextChange = useRef(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = () => {
      setReducedMotion(mediaQuery.matches);
      setMotionPreferenceReady(true);
    };

    updateMotionPreference();
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', updateMotionPreference);
      return () => mediaQuery.removeEventListener('change', updateMotionPreference);
    }
    mediaQuery.addListener(updateMotionPreference);
    return () => mediaQuery.removeListener(updateMotionPreference);
  }, []);

  const loadArticles = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const response = await getFeaturedNews();
      setArticles(response.data);
    } catch (requestError) {
      console.error('Failed to load latest news:', requestError);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadArticles();
  }, [loadArticles]);

  const syncNavigation = useCallback((instance: SwiperInstance) => {
    setNavigation(getNavigationState(instance));
  }, []);

  const syncAutoplay = useCallback((instance = swiper) => {
    if (!instance || instance.destroyed || !instance.autoplay) return;

    const visibleSlides = Number(instance.params.slidesPerView);
    const canRotate = motionPreferenceReady
      && !reducedMotion
      && articles.length > visibleSlides;

    if (!canRotate || userPausedRef.current || pointerInside.current || mouseInside.current || focusInside.current) {
      instance.autoplay.stop();
      return;
    }

    if (!instance.autoplay.running) instance.autoplay.start();
  }, [articles.length, motionPreferenceReady, reducedMotion, swiper]);

  const syncLayout = useCallback((instance: SwiperInstance) => {
    syncNavigation(instance);
    syncAutoplay(instance);
  }, [syncAutoplay, syncNavigation]);

  useEffect(() => {
    syncAutoplay();
  }, [syncAutoplay]);

  const handleSlideChange = useCallback((instance: SwiperInstance) => {
    syncLayout(instance);
    if (announceNextChange.current) {
      setAnnouncement(`Showing news story ${Math.min(instance.realIndex + 1, articles.length)} of ${articles.length}`);
      announceNextChange.current = false;
    }
  }, [articles.length, syncLayout]);

  const handleFocusLeave = (event: FocusEvent<HTMLDivElement>) => {
    const nextTarget = event.relatedTarget;
    focusInside.current = nextTarget instanceof Node && event.currentTarget.contains(nextTarget);
    syncAutoplay();
  };

  const handlePauseToggle = () => {
    const paused = !userPausedRef.current;
    userPausedRef.current = paused;
    setUserPaused(paused);
    syncAutoplay();
  };

  return (
    <section className="container section home-news-section" aria-labelledby="home-news-title">
      <div className="news-section-heading">
        <div>
          <p className="news-eyebrow">From the newsroom</p>
          <h2 id="home-news-title">Ideas in motion.</h2>
          <p>Updates, lessons, and perspectives for people building what comes next.</p>
        </div>
        <Link href="/news" className="news-view-all">
          View all news <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </div>

      {loading ? (
        <p className="news-state" role="status">Loading the latest stories…</p>
      ) : error ? (
        <div className="news-state news-state-error" role="alert">
          <span>We couldn’t load the latest stories right now.</span>
          <button type="button" className="news-retry" onClick={() => void loadArticles()}>Try again</button>
        </div>
      ) : articles.length === 0 ? (
        <p className="news-state">There are no published stories yet. Please check back soon.</p>
      ) : (
        <>
          <div
            ref={carouselRegion}
            className="home-news-carousel-region"
            role="region"
            aria-label="Latest news stories"
            aria-roledescription="carousel"
            onPointerEnter={() => {
              pointerInside.current = true;
              syncAutoplay();
            }}
            onPointerLeave={() => {
              pointerInside.current = false;
              syncAutoplay();
            }}
            onMouseEnter={() => {
              mouseInside.current = true;
              syncAutoplay();
            }}
            onMouseLeave={() => {
              mouseInside.current = false;
              syncAutoplay();
            }}
            onFocusCapture={() => {
              focusInside.current = true;
              syncAutoplay();
            }}
            onBlurCapture={handleFocusLeave}
            onKeyDownCapture={(event) => {
              if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') announceNextChange.current = true;
            }}
          >
            {articles.length > 1 && (
              <div className="news-carousel-controls" role="group" aria-label="News carousel controls">
                <button
                  type="button"
                  className="news-carousel-arrow news-carousel-arrow-prev"
                  aria-label="Show previous stories"
                  onClick={() => {
                    announceNextChange.current = true;
                    swiper?.slidePrev();
                  }}
                  disabled={!navigation.previous}
                >
                  <ArrowLeft size={18} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="news-carousel-arrow news-carousel-arrow-next"
                  aria-label="Show next stories"
                  onClick={() => {
                    announceNextChange.current = true;
                    swiper?.slideNext();
                  }}
                  disabled={!navigation.next}
                >
                  <ArrowRight size={18} aria-hidden="true" />
                </button>
                <div className="news-carousel-bottom">
                  <div className="news-carousel-bottom-row">
                    <div className="news-carousel-dots" role="group" aria-label="Choose a news story">
                      {articles.map((article, index) => (
                        <button
                          key={article.id}
                          type="button"
                          aria-label={`Show story ${index + 1}: ${article.title}`}
                          aria-current={index === activeIndex ? 'true' : undefined}
                          onClick={() => {
                            announceNextChange.current = true;
                            if (articles.length >= 3) swiper?.slideToLoop(index);
                            else swiper?.slideTo(index);
                          }}
                        />
                      ))}
                    </div>
                    {motionPreferenceReady && !reducedMotion && (
                      <button
                        type="button"
                        className="news-autoplay-toggle"
                        aria-label={userPaused ? 'Resume automatic news rotation' : 'Pause automatic news rotation'}
                        onClick={handlePauseToggle}
                      >
                        {userPaused
                          ? <Play size={17} aria-hidden="true" />
                          : <Pause size={17} aria-hidden="true" />}
                        <span>{userPaused ? 'Resume' : 'Pause'}</span>
                      </button>
                    )}
                  </div>
                  <div
                    className="news-carousel-progress"
                    role="progressbar"
                    aria-label="News story progress"
                    aria-valuemin={0}
                    aria-valuemax={articles.length}
                    aria-valuenow={activeIndex + 1}
                  >
                    <span style={{ width: `${((activeIndex + 1) / articles.length) * 100}%` }} />
                  </div>
                </div>
              </div>
            )}
            <Swiper
              className="news-carousel"
              modules={[A11y, Autoplay, Keyboard]}
              keyboard={{ enabled: true, onlyInViewport: true }}
              a11y={{
                enabled: true,
                prevSlideMessage: 'Previous news stories',
                nextSlideMessage: 'Next news stories',
                wrapperLiveRegion: false,
              }}
              autoplay={{
                enabled: false,
                delay: 5000,
                disableOnInteraction: false,
                pauseOnMouseEnter: false,
                waitForTransition: true,
              }}
              loop={articles.length >= 3}
              rewind={articles.length === 2}
              slidesPerView={1}
              spaceBetween={0}
              onSwiper={(instance) => {
                setSwiper(instance);
                setActiveIndex(instance.realIndex);
                syncNavigation(instance);
                syncAutoplay(instance);
                setAnnouncement(`Showing news story ${Math.min(instance.realIndex + 1, articles.length)} of ${articles.length}`);
              }}
              onSlideChange={(instance) => {
                setActiveIndex(instance.realIndex);
                handleSlideChange(instance);
              }}
              onBreakpoint={syncLayout}
              onResize={syncLayout}
            >
              {articles.map((article) => (
                <SwiperSlide key={article.id}>
                  <NewsArticleCard article={article} featured />
                </SwiperSlide>
              ))}
            </Swiper>
            <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
              {announcement}
            </p>
          </div>
        </>
      )}
    </section>
  );
}
