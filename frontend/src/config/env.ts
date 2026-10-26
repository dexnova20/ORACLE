/**
 * Environment configuration for the frontend client.
 */

export const env = {
  /**
   * Base URL for the ORACLE backend API.
   * Defaults to http://localhost:8000 for local development.
   */
  apiUrl: process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") || "http://localhost:8000",
} as const;
