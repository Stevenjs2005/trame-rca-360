import ImageDisplayArea from './ImageDisplayArea.js';
import MediaSourceDisplayArea from './MediaSourceDisplayArea.js';
import VideoDecoderDisplayArea from './VideoDecoderDisplayArea.js';
import RawImageDisplayArea from './RawImageDisplayArea.js';
import ImageDisplayArea360 from './ImageDisplayArea360.js';
export default {
  components: {
    ImageDisplayArea,
    MediaSourceDisplayArea,
    VideoDecoderDisplayArea,
    RawImageDisplayArea,
    ImageDisplayArea360,
  },
  props: {
    name: {
      type: String,
      default: 'default',
    },
    origin: {
      type: String,
      default: 'anonymous',
    },
    display: {
      type: String,
      default: 'image',
    },
    imageStyle: {
      type: Object,
      default: () => ({ width: '100%' }),
    },staticImage: {
      type: String,
      default: null,
    },
  },
  template: `
    <div style="width: 100%; height: 100%; display: flex; justify-content: center; align-items: center;">
      <image-display-area v-if="display === 'image'" :name="name" :origin="origin" :poolSize="4" :imageStyle="imageStyle" />
      <media-source-display-area v-if="display === 'media-source'" :name="name" :origin="origin" />
      <video-decoder-display-area v-if="display === 'video-decoder'" :name="name" :origin="origin" />
      <raw-image-display-area v-if="display === 'raw-image'" :name="name" :origin="origin" :imageStyle="imageStyle" />
      <image-display-area-360 v-if="display === 'image-360'" :name="name" :origin="origin" :imageStyle="imageStyle" :staticImage="staticImage" />
      </div>
  `,
};
