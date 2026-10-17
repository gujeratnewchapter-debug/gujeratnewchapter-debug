import test from 'node:test';
import assert from 'node:assert/strict';
import { STRINGS, translate } from './translations.ts';

const supportedLanguages = ['en', 'am', 'om', 'ti'];

test('every translation key has a non-empty value in every supported language', () => {
  for (const [key, values] of Object.entries(STRINGS)) {
    for (const language of supportedLanguages) {
      assert.equal(typeof values[language], 'string', `${key} is missing ${language}`);
      assert.ok(values[language].trim(), `${key} has an empty ${language} translation`);
    }
  }
});

test('translation lookup returns the requested language and preserves English fallback', () => {
  assert.equal(translate('contactTeam', 'om'), STRINGS.contactTeam.om);
  assert.equal(translate('contactTeam', 'en'), 'Contact the team');
});
