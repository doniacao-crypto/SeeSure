/**
 * AI-SDLC Template - Sample Entry Point
 * Replace with your actual application code.
 */

export function greet(name: string): string {
  if (!name || name.trim() === '') {
    throw new Error('Name is required');
  }
  return `Hello, ${name}! Welcome to AI-SDLC.`;
}

export function add(a: number, b: number): number {
  return a + b;
}

// Main entry point
/* istanbul ignore next */
if (require.main === module) {
  // eslint-disable-next-line no-console
  console.log(greet('Developer'));
  // eslint-disable-next-line no-console
  console.log('Setup complete! Start building with:');
  // eslint-disable-next-line no-console
  console.log('  claude "/kiro:spec-init Your feature description"');
}
