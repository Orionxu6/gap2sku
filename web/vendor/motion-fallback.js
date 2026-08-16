(function () {
  "use strict";

  if (window.Motion) {
    document.documentElement.dataset.motionEngine = "motion-12.42.2";
    return;
  }

  const asElements = (target) => {
    if (typeof target === "string") return [...document.querySelectorAll(target)];
    if (target instanceof Element) return [target];
    return [...(target || [])].filter((item) => item instanceof Element);
  };

  const framesFor = (values) => {
    const entries = Object.entries(values || {});
    const frameCount = Math.max(1, ...entries.map(([, value]) => Array.isArray(value) ? value.length : 1));
    return Array.from({length: frameCount}, (_, index) => {
      const frame = {};
      let x = null;
      let y = null;
      let scale = null;
      entries.forEach(([property, raw]) => {
        const sequence = Array.isArray(raw) ? raw : [raw];
        const value = sequence[Math.min(index, sequence.length - 1)];
        if (property === "x") x = value;
        else if (property === "y") y = value;
        else if (property === "scale") scale = value;
        else frame[property] = value;
      });
      if (x !== null || y !== null || scale !== null) {
        frame.transform = `translate(${x || 0}px, ${y || 0}px) scale(${scale === null ? 1 : scale})`;
      }
      return frame;
    });
  };

  const animate = (target, values, options = {}) => {
    const elements = asElements(target);
    return elements.map((element, index) => {
      const delay = typeof options.delay === "function" ? options.delay(index) : (options.delay || 0);
      return element.animate(framesFor(values), {
        duration: (options.duration || 0.35) * 1000,
        delay: delay * 1000,
        easing: options.easing || "ease-out",
        fill: "both",
      });
    });
  };

  const stagger = (interval = 0.05, options = {}) => (index) => (options.startDelay || 0) + index * interval;

  const inView = (target, callback, options = {}) => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        callback(entry.target);
        observer.unobserve(entry.target);
      });
    }, {threshold: options.amount || 0.14});
    asElements(target).forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  };

  window.Motion = {animate, stagger, inView, source: "native-fallback"};
  document.documentElement.dataset.motionEngine = "native-waapi-fallback";
})();
