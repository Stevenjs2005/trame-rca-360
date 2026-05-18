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

  watch: {
    staticImage(newImage) {
      if (!newImage) return;
      if (!this.dome) {
        this.createDome(newImage);  // first image — create the dome
      } else {
        this.setDomeTexture(newImage);  // subsequent images — swap texture
      }
    },
  },

  methods: {
    // ----------------------------
    // Babylon Setup
    // ----------------------------
    initBabylon() {
      const canvas = this.$refs.canvas;
      if (!canvas) {
        console.error("Canvas ref not found");
        return;
      }
    
      this.engine = new BABYLON.Engine(canvas, true);
      this.scene = new BABYLON.Scene(this.engine);
    
      this.camera = new BABYLON.UniversalCamera(
        "camera",
        BABYLON.Vector3.Zero(),
        this.scene
      );
      this.camera.minZ = 0.1;
      this.camera.attachControl(canvas, true);
      // Allow looking around by clicking and dragging
      this.camera.inputs.addMouseWheel();  // optional: zoom
      this.camera.speed = 0;               // disable WASD movement — you're inside a sphere
      this.camera.angularSensibility = 500; // lower = faster mouse look (default 2000)

      // Only create the dome if a real image is available at mount time.
      // If not, the watcher will call createDome() when staticImage first arrives.
      if (this.staticImage) {
        this.createDome(this.staticImage);
      }
    
      // WebXR
      if (navigator.xr) {
        this.scene.createDefaultXRExperienceAsync({
          uiOptions: { sessionMode: "immersive-vr" },
          optionalFeatures: true,
        }).then((xr) => {
          this.xrHelper = xr;
          xr.baseExperience.onStateChangedObservable.add((state) => {
            if (state === BABYLON.WebXRState.IN_XR) {
              console.log("VR session active");
            }
            if (state === BABYLON.WebXRState.NOT_IN_XR) {
              console.log("VR session ended");
            }
          });
        }).catch((err) => {
          console.warn("WebXR not available:", err);
        });
      }
    
      this.engine.runRenderLoop(() => {
        if (this.scene) this.scene.render();
      });
    
      window.addEventListener("resize", this.handleResize);
    },

    handleResize() {
      if (this.engine) {
        this.engine.resize();
      }
    },

    createDome(url) {
      if (this.dome) {
        this.dome.dispose();
      }
      this.dome = new BABYLON.PhotoDome(
        "anari-dome",
        url,
        { resolution: 32, size: 1000 },
        this.scene,
      );
      this.dome.imageMode = BABYLON.PhotoDome.MODE_TOPBOTTOM;
      console.log("PhotoDome created with MODE_TOPBOTTOM");
    },

    setDomeTexture(url) {
      if (!this.dome) return;
      if (this.dome.texture) {
        this.dome.texture.dispose();
      }
      this.dome.texture = new BABYLON.Texture(
        url, this.scene, true, false,
        BABYLON.Texture.TRILINEAR_SAMPLINGMODE
      );
      // Re-apply after every texture swap
      this.dome.imageMode = BABYLON.PhotoDome.MODE_TOPBOTTOM;
      console.log("new SetDomeTexture method added");
    },

    //subscribe to trame stream
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

    //update streaming texture
    updateDomeTexture(type, content) {
      const blob = new Blob([content], { type });
      const url = URL.createObjectURL(blob);
      this.setDomeTexture(url);
      this.dome.texture.onLoadObservable?.addOnce(() =>
        URL.revokeObjectURL(url)
      );
      console.log("updateDomeTexture Called");
    },

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
