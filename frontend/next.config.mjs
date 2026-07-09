/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Produces a standalone server bundle so the Docker image stays small.
  output: "standalone",
};

export default nextConfig;
