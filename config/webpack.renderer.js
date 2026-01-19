const path = require('path');
const { merge } = require('webpack-merge');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const common = require('./webpack.common');
const paths = require('./paths');

module.exports = (env, argv) => {
  const isDevelopment = argv.mode === 'development';

  return merge(common, {
    target: 'electron-renderer',

    entry: {
      pet: paths.petEntry,
      dashboard: paths.dashboardEntry,
    },

    output: {
      path: paths.distRenderer,
      filename: '[name]/bundle.js',
      clean: true,
    },

    devtool: isDevelopment ? 'cheap-module-source-map' : false,

    plugins: [
      // Pet window HTML
      new HtmlWebpackPlugin({
        filename: 'pet/index.html',
        template: paths.petTemplate,
        chunks: ['pet'],
        inject: 'body',
        minify: !isDevelopment,
      }),

      // Dashboard window HTML
      new HtmlWebpackPlugin({
        filename: 'dashboard/index.html',
        template: paths.dashboardTemplate,
        chunks: ['dashboard'],
        inject: 'body',
        minify: !isDevelopment,
      }),

      // Copy public assets
      new CopyWebpackPlugin({
        patterns: [
          {
            from: paths.publicAssets,
            to: path.resolve(paths.distRenderer, 'assets'),
            noErrorOnMissing: true,
          },
        ],
      }),
    ],

    optimization: {
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          // React and React-DOM
          react: {
            test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
            name: 'vendor-react',
            priority: 20,
          },
          // Radix UI components
          radix: {
            test: /[\\/]node_modules[\\/](@radix-ui)[\\/]/,
            name: 'vendor-radix',
            priority: 15,
          },
          // Other vendor libraries
          vendors: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            priority: 10,
          },
        },
      },
    },

    devServer: {
      static: {
        directory: paths.dist,
      },
      port: 8080,
      hot: true,
      historyApiFallback: true,
      headers: {
        'Access-Control-Allow-Origin': '*',
      },
    },
  });
};
