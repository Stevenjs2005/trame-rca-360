import * as BABYLON from "@babylonjs/core";
 // import * as loaders from "@babylonjs/loaders";

export default {
  props: {
    name: {
      type: String,
      default: "default",
    },
    origin: {
      type: String,
      default: "anonymous",
    },
    imageStyle: {
      type: Object,
      default: () => ({ width: "100%", height: "100%" }),
    },
    staticImage: {
      type: String,
      default: null,
    },
  },

  inject: ["trame"],
  template: `
    <canvas
      ref="canvas"
      :style="imageStyle"
    ></canvas>`,
  mounted() {
    this.$nextTick(() => {
      this.initBabylon();

      if (!this.staticImage) {
        this.subscribeToStream();
      }
    });
  },

  beforeUnmount() {
    this.cleanup();
  },

  beforeDestroy() {
    this.cleanup();
  },

  methods: {
    // ----------------------------
    // Babylon Setup
    // ----------------------------
    initBabylon() {
      console.log("__init__")
      const canvas = this.$refs.canvas;
      if (!canvas) {
        console.error("Canvas ref not found");
        return;
      }
      console.log("canvas created")
      this.engine = new BABYLON.Engine(canvas, true);
      console.log("engine created")
      this.scene = new BABYLON.Scene(this.engine);
      console.log("scene created")
      // Camera inside sphere
      this.camera = new BABYLON.ArcRotateCamera(
        "camera",
        Math.PI / 2,
        Math.PI / 2,
        1,
        BABYLON.Vector3.Zero(),
        this.scene
      );
      console.log("camera created")
      this.camera.attachControl(canvas, true);
      this.camera.wheelPrecision = 50;
      this.camera.minZ = 0.1;

      // Use static image if provided
      console.log("camera attached")
      console.log("testing static image")
      const domeTexture = this.staticImage || "Waiting for Rendered Image";
      console.log(domeTexture)
      try {
        this.dome = new BABYLON.PhotoDome(
          "anari-dome",
          domeTexture,
          { resolution: 32, size: 1000 },
          this.scene
        );
      } catch (e) {we
        console.error("PhotoDome failed:", e);
      }
      console.log("Photodome Created")
      // Render loop
      this.engine.runRenderLoop(() => {
        if (this.scene) {
          this.scene.render();
        }
      });
      window.addEventListener("resize", this.handleResize);
    },

    handleResize() {
      if (this.engine) {
        this.engine.resize();
      }
    },

    // ----------------------------
    // Stream Subscription
    // ----------------------------
    subscribeToStream() {
      if (!this.trame) return;

      this.onImage = ([{ name, meta, content }]) => {
        if (this.name !== name) return;

        const supportedImageTypes = [
          "image/jpeg",
          "image/png",
          "image/webp",
        ];

        if (!supportedImageTypes.includes(meta.type)) return;

        this.updateDomeTexture(meta.type, content);
      };

      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe("trame.rca.topic.stream", this.onImage);
    },

    // ----------------------------
    // Streaming Texture Update
    // ----------------------------
    updateDomeTexture(type, content) {
      const blob = new Blob([content], { type });
      const url = URL.createObjectURL(blob);

      if (!this.dome) return;

      // Properly dispose old texture
      if (this.dome.texture) {
        this.dome.texture.dispose();
      }

      this.dome.texture = new BABYLON.Texture(
        url,
        this.scene,
        true,
        false,
        BABYLON.Texture.TRILINEAR_SAMPLINGMODE,
        () => {
          URL.revokeObjectURL(url);
        }
      );
    },

    // ----------------------------
    // Cleanup
    // ----------------------------
    cleanup() {
      if (this.wslinkSubscription && this.trame) {
        this.trame.client
          .getConnection()
          .getSession()
          .unsubscribe(this.wslinkSubscription);
        this.wslinkSubscription = null;
      }

      window.removeEventListener("resize", this.handleResize);

      if (this.engine) {
        this.engine.dispose();
        this.engine = null;
      }
    },
  },
};
