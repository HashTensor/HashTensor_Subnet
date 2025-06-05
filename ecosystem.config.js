module.exports = {
  apps: [
    {
      name: "hashtensor-validator",
      script: "./entrypoint.sh",
      env: {
        PORT: 8000,
        DATABASE_URL: "sqlite:///data/mapping.db",
        PROMETHEUS_ENDPOINT: "http://pool.hashtensor.com:9090",
        WALLET_NAME: "default",
        WALLET_HOTKEY: "default",
        WALLET_PATH: "~/.bittensor/wallets/",
        SUBTENSOR_NETWORK: "finney",
      }
    }
  ]
};