import type { Lang } from '../../types'

export interface FxText { label: string; full: string; reduced: string; off: string; auto: string; phone: string }

/** Hindi and Marathi are AI drafts. */
export const FXTEXT: Record<Lang, FxText> = {
  en: { label: 'Visual effects', full: 'Full', reduced: 'Reduced', off: 'Off', auto: 'Effects were reduced automatically to keep the call smooth.', phone: 'Phone call simulation' },
  hi: { label: 'विज़ुअल इफ़ेक्ट', full: 'पूरे', reduced: 'कम', off: 'बंद', auto: 'कॉल को सहज रखने के लिए इफ़ेक्ट अपने-आप कम कर दिए गए।', phone: 'फ़ोन कॉल सिमुलेशन' },
  mr: { label: 'व्हिज्युअल इफेक्ट', full: 'पूर्ण', reduced: 'कमी', off: 'बंद', auto: 'कॉल सुरळीत ठेवण्यासाठी इफेक्ट आपोआप कमी केले.', phone: 'फोन कॉल सिम्युलेशन' },
}
