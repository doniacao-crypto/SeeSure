import { greet, add } from '../../src/index';

describe('greet', () => {
  it('should return greeting with name', () => {
    expect(greet('Alice')).toBe('Hello, Alice! Welcome to AI-SDLC.');
  });

  it('should throw error for empty name', () => {
    expect(() => greet('')).toThrow('Name is required');
  });
});

describe('add', () => {
  it('should add two numbers', () => {
    expect(add(2, 3)).toBe(5);
  });

  it('should handle negative numbers', () => {
    expect(add(-1, -2)).toBe(-3);
  });
});
