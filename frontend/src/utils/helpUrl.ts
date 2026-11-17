export const DEFAULT_HELP_URL = 'https://docs.fit2cloud.com/sqlbot/'

const legacyDefaultHelpUrl = /^https:\/\/dataease\.cn\/sqlbot(?:\/v1)?\/?$/

export const resolveHelpUrl = (url?: string | null): string => {
  return !url || legacyDefaultHelpUrl.test(url) ? DEFAULT_HELP_URL : url
}
