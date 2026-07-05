/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    // Enable App Router (src/app directory)
    appDir: true,
  },
};

module.exports = nextConfig;
