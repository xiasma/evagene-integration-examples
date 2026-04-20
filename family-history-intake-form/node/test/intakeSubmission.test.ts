import { deepStrictEqual, strictEqual, throws } from 'node:assert/strict';
import { test } from 'node:test';

import {
  IntakeValidationError,
  parseIntakeSubmission,
} from '../src/intakeSubmission.js';

test('minimal submission keeps only proband', () => {
  const submission = parseIntakeSubmission({ proband_name: 'Emma Smith' });

  strictEqual(submission.proband.displayName, 'Emma Smith');
  strictEqual(submission.proband.biologicalSex, 'unknown');
  strictEqual(submission.proband.yearOfBirth, undefined);
  strictEqual(submission.mother, undefined);
  strictEqual(submission.father, undefined);
  deepStrictEqual(submission.siblings, []);
});

test('proband name is required', () => {
  throws(() => parseIntakeSubmission({}), IntakeValidationError);
  throws(() => parseIntakeSubmission({ proband_name: '   ' }), IntakeValidationError);
});

test('parses proband sex and year of birth', () => {
  const submission = parseIntakeSubmission({
    proband_name: 'Emma',
    proband_sex: 'female',
    proband_year: '1985',
  });

  strictEqual(submission.proband.biologicalSex, 'female');
  strictEqual(submission.proband.yearOfBirth, 1985);
});

test('rejects unknown biological sex', () => {
  throws(
    () => parseIntakeSubmission({ proband_name: 'Emma', proband_sex: 'robot' }),
    IntakeValidationError,
  );
});

test('rejects out-of-range year of birth', () => {
  throws(
    () => parseIntakeSubmission({ proband_name: 'Emma', proband_year: '1700' }),
    IntakeValidationError,
  );
  throws(
    () => parseIntakeSubmission({ proband_name: 'Emma', proband_year: '2999' }),
    IntakeValidationError,
  );
});

test('includes mother when provided, otherwise omits', () => {
  const withMother = parseIntakeSubmission({
    proband_name: 'Emma',
    mother_name: 'Grace Smith',
    mother_year: '1960',
  });
  deepStrictEqual(withMother.mother, { displayName: 'Grace Smith', yearOfBirth: 1960 });

  const withoutMother = parseIntakeSubmission({
    proband_name: 'Emma',
    mother_name: '  ',
  });
  strictEqual(withoutMother.mother, undefined);
});

test('parses siblings and assigns sex from relation', () => {
  const submission = parseIntakeSubmission({
    proband_name: 'Emma',
    sibling_0_name: 'Alice',
    sibling_0_relation: 'sister',
    sibling_0_year: '1988',
    sibling_1_name: 'Bob',
    sibling_1_relation: 'half_brother',
  });

  strictEqual(submission.siblings.length, 2);
  const [first, second] = submission.siblings;
  deepStrictEqual(first, {
    displayName: 'Alice',
    relation: 'sister',
    biologicalSex: 'female',
    yearOfBirth: 1988,
  });
  deepStrictEqual(second, {
    displayName: 'Bob',
    relation: 'half_brother',
    biologicalSex: 'male',
  });
});

test('skips blank sibling rows', () => {
  const submission = parseIntakeSubmission({
    proband_name: 'Emma',
    sibling_0_name: 'Alice',
    sibling_0_relation: 'sister',
    sibling_2_name: 'Carol',
    sibling_2_relation: 'sister',
  });

  strictEqual(submission.siblings.length, 2);
  strictEqual(submission.siblings[0]?.displayName, 'Alice');
  strictEqual(submission.siblings[1]?.displayName, 'Carol');
});

test('sibling without a relation rejects the whole submission', () => {
  throws(
    () =>
      parseIntakeSubmission({
        proband_name: 'Emma',
        sibling_0_name: 'Alice',
        sibling_0_relation: '',
      }),
    IntakeValidationError,
  );
});
