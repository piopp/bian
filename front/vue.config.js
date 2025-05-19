const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 8080,  // 前端开发服务器端口
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // 可选：如果你的后端 API 路径没有 /api 前缀，可以用 pathRewrite 去掉它
        // pathRewrite: { '^/api': '' }
      }
    }
  },
  chainWebpack: config => {
    config.module
      .rule('js')
      .use('babel-loader')
      .tap(options => {
        options.cacheDirectory = false;
        return options;
      });
  }
})
