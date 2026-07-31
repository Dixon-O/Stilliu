/// <reference types="vite/client" />

// Pulls in Vite's ambient module declarations, which is what makes importing a
// static asset (`import url from '@/assets/x.png'`) type-check as a string.
// Without this file TypeScript rejects the import outright.
