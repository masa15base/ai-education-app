import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'app.manatomo.education',
  appName: 'まなとも',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
