// EAS file variables contain a path, never the JSON value itself.
// Keep the local fallback for existing developer checkouts.
module.exports = ({config}) => ({
  ...config,
  android: {
    ...config.android,
    googleServicesFile: process.env.GOOGLE_SERVICES_JSON || './google-services.json',
  },
});
