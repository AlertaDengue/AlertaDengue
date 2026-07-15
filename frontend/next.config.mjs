export const DJANGO_PORT = process.env.DJANGO_PORT;

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  output: "standalone",

  experimental: {
    optimizePackageImports: ["@tanstack/react-query", "axios", "lucide-react", "date-fns", "lodash"],
  },

  compress: true,

  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.optimization.splitChunks = {
        chunks: "all",
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: "vendors",
            chunks: "all",
            maxSize: 244000,
          },
          common: {
            name: "common",
            minChunks: 2,
            chunks: "all",
            enforce: true,
            maxSize: 244000,
          },
        },
      };
    }

    return config;
  },

  async redirects() {
    return [];
  },

  async rewrites() {
    return [];
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
