const path = require('path');
const { merge } = require('webpack-merge');
const common = require('./webpack.common');
const paths = require('./paths');

module.exports = merge(common, {
  target: 'electron-main',

  entry: {
    main: paths.mainEntry,
  },

  output: {
    path: paths.distMain,
    filename: '[name].js',
    libraryTarget: 'commonjs2',
  },

  externals: {
    // Don't bundle electron or native modules
    electron: 'commonjs2 electron',
    '@anthropic-ai/claude-agent-sdk': 'commonjs2 @anthropic-ai/claude-agent-sdk',
  },

  node: {
    __dirname: false,
    __filename: false,
  },

  module: {
    rules: [
      {
        test: /\.ts$/,
        exclude: /node_modules/,
        use: {
          loader: 'ts-loader',
          options: {
            transpileOnly: true,
            configFile: path.resolve(paths.root, 'tsconfig.main.json'),
          },
        },
      },
    ],
  },
});
