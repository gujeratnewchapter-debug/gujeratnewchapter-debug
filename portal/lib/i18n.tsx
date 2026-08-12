'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

export type Lang = 'en' | 'am' | 'om' | 'ti';

export const LANGUAGES: { code: Lang; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'am', label: 'አማርኛ' },
  { code: 'om', label: 'Afaan Oromoo' },
  { code: 'ti', label: 'ትግርኛ' },
];

// Site-wide strings. Extend this dictionary as more copy is translated —
// every component pulls text through t() so adding a language here makes
// it live everywhere immediately.
const STRINGS: Record<string, Record<Lang, string>> = {
  home: { en: 'Home', am: 'መነሻ', om: 'Mana', ti: 'መደብ' },
  aiTutor: { en: 'AI Tutor', am: 'AI አስተማሪ', om: 'Barsiisaa AI', ti: 'AI መምህር' },
  courses: { en: 'Courses', am: 'ኮርሶች', om: 'Koorsii', ti: 'ኮርስታት' },
  signIn: { en: 'Sign in', am: 'ግባ', om: 'Seeni', ti: 'እቶ' },
  signUp: { en: 'Sign up', am: 'ተመዝገብ', om: 'Galmaa\'i', ti: 'ተመዝገብ' },
  continueWithGoogle: { en: 'Continue with Google', am: 'በGoogle ይቀጥሉ', om: 'Google\'n itti fufi', ti: 'ብ Google ቀጽል' },
  continueWithEmail: { en: 'Continue with email', am: 'በኢሜይል ይቀጥሉ', om: 'Imeeliidhaan itti fufi', ti: 'ብ ኢመይል ቀጽል' },
  searchPlaceholder: { en: 'Search courses...', am: 'ኮርሶችን ይፈልጉ...', om: 'Koorsii barbaadi...', ti: 'ኮርስታት ድለ...' },
  heroTitle: {
    en: 'Learn to build. Build to grow.',
    am: 'ለመገንባት ተማር። ለማደግ ገንባ።',
    om: 'Ijaaruuf baradhu. Guddachuuf ijaari.',
    ti: 'ንምህናጽ ተመሃር። ንዕብየት ህነጽ።',
  },
  heroSubtitle: {
    en: 'Ethiopia\'s home for entrepreneurship, AI, and business education — with an AI Tutor at every step.',
    am: 'ለስራ ፈጠራ፣ ለ AI እና ለንግድ ትምህርት የኢትዮጵያ መገኛ — በእያንዳንዱ እርምጃ የ AI አስተማሪ ጋር።',
    om: 'Mana barnoota ogummaa hojii, AI fi daldalaa Itoophiyaa — Barsiisaa AI tarkaanfii hundaan.',
    ti: 'ቤት ትምህርቲ ስራሕ ፈጠራን ንግድን ኢትዮጵያ — ምስ AI መምህር ኣብ ነፍሲ ወከፍ ስጉምቲ።',
  },
  exploreCourses: { en: 'Explore Courses', am: 'ኮርሶችን ያስሱ', om: 'Koorsii Sakatta\'i', ti: 'ኮርስታት ርአ' },
  dashboard: { en: 'Dashboard', am: 'ዳሽቦርድ', om: 'Daashboordii', ti: 'ዳሽቦርድ' },
  profile: { en: 'Profile', am: 'መገለጫ', om: 'Piroofaayilii', ti: 'መግለጺ' },
  logOut: { en: 'Log out', am: 'ውጣ', om: 'Ba\'i', ti: 'ውጻእ' },
  yourProgress: { en: 'Your Progress', am: 'የእርስዎ ግስጋሴ', om: 'Adeemsa Kee', ti: 'ናትካ ማዕበል' },
  contactUs: { en: 'Contact Us', am: 'ያግኙን', om: 'Nu Qunnamaa', ti: 'ርኸቡና' },
  supportUs: { en: 'Support Us', am: 'ይደግፉን', om: 'Nu Deeggaraa', ti: 'ደግፉና' },
  yourName: { en: 'Your name', am: 'ስምዎ', om: 'Maqaa kee', ti: 'ስምካ' },
  yourEmail: { en: 'Your email', am: 'ኢሜይልዎ', om: 'Imeelii kee', ti: 'ኢመይልካ' },
  subject: { en: 'Subject', am: 'ርዕሰ ጉዳይ', om: 'Mata duree', ti: 'ኣርእስቲ' },
  message: { en: 'Message', am: 'መልእክት', om: 'Ergaa', ti: 'መልእኽቲ' },
  sendMessage: { en: 'Send Message', am: 'መልእክት ላክ', om: 'Ergaa Ergi', ti: 'መልእኽቲ ስደድ' },
};

interface I18nContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: keyof typeof STRINGS) => string;
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>('en');

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? window.localStorage.getItem('ess_lang') : null;
    if (stored && LANGUAGES.some((l) => l.code === stored)) setLangState(stored as Lang);
  }, []);

  function setLang(l: Lang) {
    setLangState(l);
    if (typeof window !== 'undefined') window.localStorage.setItem('ess_lang', l);
  }

  function t(key: keyof typeof STRINGS): string {
    return STRINGS[key]?.[lang] ?? STRINGS[key]?.en ?? String(key);
  }

  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within I18nProvider');
  return ctx;
}
