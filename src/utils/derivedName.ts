const NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$/;

/** Validate a stored-object name exactly like the backend's validate_derived_name. */
export function nameError(name: string): string | null {
  if (name === '') return 'Enter a name';
  if (name !== name.trim()) return 'Name must not start or end with whitespace';
  if (!NAME_PATTERN.test(name)) {
    return "1–64 characters: letters, digits, spaces, '.', '_' or '-', starting with a letter or digit";
  }
  return null;
}
