const dataSource = process.env.GRIDCAST_DATA_SOURCE ?? 'fixtures';

if (dataSource === 'cos' && !process.env.COS_BASE_URL) {
  throw new Error('COS_BASE_URL must be set when GRIDCAST_DATA_SOURCE=cos');
}

/** @type {import('next').NextConfig} */
const nextConfig = {};

export default nextConfig;
