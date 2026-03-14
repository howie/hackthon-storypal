import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import zhTWCommon from './locales/zh-TW/common.json'
import zhTWStory from './locales/zh-TW/story.json'
import zhTWAuth from './locales/zh-TW/auth.json'
import zhTWInteraction from './locales/zh-TW/interaction.json'

import enCommon from './locales/en/common.json'
import enStory from './locales/en/story.json'
import enAuth from './locales/en/auth.json'
import enInteraction from './locales/en/interaction.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      'zh-TW': {
        common: zhTWCommon,
        story: zhTWStory,
        auth: zhTWAuth,
        interaction: zhTWInteraction,
      },
      en: {
        common: enCommon,
        story: enStory,
        auth: enAuth,
        interaction: enInteraction,
      },
    },
    defaultNS: 'common',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'storypal-lang',
      caches: ['localStorage'],
    },
    initImmediate: false,
  })

export default i18n
