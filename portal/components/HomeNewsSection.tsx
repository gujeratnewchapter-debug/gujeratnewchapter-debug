'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { A11y, Keyboard } from 'swiper/modules';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperInstance } from 'swiper';
import 'swiper/css';

import { getFeaturedNews, type NewsArticle } from '@/lib/api';
import { NewsArticleCard } from '@/components/NewsArticleCard';

type NavigationState = { previous: boolean; next: boolean };

function getNavigationState(swiper: SwiperInstance): NavigationState {
  return { previous: !swiper.isBeginning, next: !swiper.isEnd };
}

export function HomeNewsSection() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [swiper, setSwiper] = useState<SwiperInstance | null>(null);
  const [navigation, setNavigation] = useState<NavigationState>({ previous: false, next: false });

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
          <div className="news-carousel-controls" aria-label="News carousel controls">
            <button
              type="button"
              aria-label="Show previous stories"
              onClick={() => swiper?.slidePrev()}
              disabled={!navigation.previous}
            >
              <ArrowLeft size={18} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Show more stories"
              onClick={() => swiper?.slideNext()}
              disabled={!navigation.next}
            >
              <ArrowRight size={18} aria-hidden="true" />
            </button>
          </div>
          <Swiper
            className="news-carousel"
            modules={[A11y, Keyboard]}
            keyboard={{ enabled: true, onlyInViewport: true }}
            a11y={{ enabled: true, prevSlideMessage: 'Previous news stories', nextSlideMessage: 'Next news stories' }}
            slidesPerView={1}
            spaceBetween={16}
            breakpoints={{
              640: { slidesPerView: Math.min(2, articles.length), spaceBetween: 20 },
              1024: { slidesPerView: Math.min(3, articles.length), spaceBetween: 24 },
            }}
            onSwiper={(instance) => {
              setSwiper(instance);
              syncNavigation(instance);
            }}
            onSlideChange={syncNavigation}
            onBreakpoint={syncNavigation}
            onResize={syncNavigation}
          >
            {articles.map((article) => (
              <SwiperSlide key={article.id}>
                <NewsArticleCard article={article} />
              </SwiperSlide>
            ))}
          </Swiper>
          <p className="sr-only" aria-live="polite">
            Showing news story {Math.min((swiper?.activeIndex ?? 0) + 1, articles.length)} of {articles.length}
          </p>
        </>
      )}
    </section>
  );
}
