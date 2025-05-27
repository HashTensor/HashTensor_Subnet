module.exports = {
  apps: [
    {
      name: "hashtensor-validator",
      script: "./entrypoint.sh",
      env: {
        PROMETHEUS_ENDPOINT: "http://194.135.93.138:9090"
      }
    }
  ]
};