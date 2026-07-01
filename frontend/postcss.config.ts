import autoprefixer from 'autoprefixer'
import postcssPresetEnv from 'postcss-preset-env'
import cssHasPseudo from 'css-has-pseudo'

export default {
  plugins: [
    cssHasPseudo({ preserve: true }),
    autoprefixer(),
    postcssPresetEnv({
      stage: 3,
      browsers: 'Chrome 81',
    }),
  ],
}
