const path = require('path');
const paths = require('./paths');

module.exports = {
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    alias: {
      '@main': paths.main,
      '@renderer': paths.renderer,
      '@shared': paths.rendererShared,
      '@core': paths.core,
      '@types': paths.types,
      '@utils': paths.utils,
    },
  },

  module: {
    rules: [
      // TypeScript loader
      {
        test: /\.tsx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'ts-loader',
          options: {
            transpileOnly: true, // Speed up compilation
            configFile: path.resolve(paths.root, 'tsconfig.renderer.json'),
          },
        },
      },

      // CSS loader (for Tailwind)
      {
        test: /\.css$/,
        use: [
          'style-loader',
          'css-loader',
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                config: path.resolve(paths.root, 'postcss.config.js'),
              },
            },
          },
        ],
      },

      // Image loader
      {
        test: /\.(png|jpg|jpeg|gif|svg)$/,
        type: 'asset/resource',
        generator: {
          filename: 'assets/images/[name][ext]',
        },
      },

      // Font loader
      {
        test: /\.(woff|woff2|eot|ttf|otf)$/,
        type: 'asset/resource',
        generator: {
          filename: 'assets/fonts/[name][ext]',
        },
      },
    ],
  },

  stats: {
    colors: true,
    modules: false,
    children: false,
    chunks: false,
    chunkModules: false,
  },
};
