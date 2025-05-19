/**
 * 性能优化工具函数
 * 包含防抖、节流以及ResizeObserver错误处理等功能
 */

/**
 * 通用防抖函数
 * @param {Function} fn 需要防抖的函数
 * @param {Number} delay 延迟时间，单位毫秒
 * @returns {Function} 防抖处理后的函数
 */
export function debounce(fn, delay = 200) {
  let timer = null;
  return function(...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

/**
 * 通用节流函数
 * @param {Function} fn 需要节流的函数
 * @param {Number} interval 间隔时间，单位毫秒
 * @returns {Function} 节流处理后的函数
 */
export function throttle(fn, interval = 200) {
  let lastTime = 0;
  return function(...args) {
    const now = Date.now();
    if (now - lastTime >= interval) {
      lastTime = now;
      fn.apply(this, args);
    }
  };
}

/**
 * 全局处理ResizeObserver错误
 * 在应用入口处调用一次即可
 */
export function handleResizeObserverErrors() {
  // 第一种解决方案：拦截错误事件
  const errorHandler = event => {
    if (event && event.message && (
      event.message.includes('ResizeObserver') || 
      event.message.includes('ResizeObserver loop completed with undelivered notifications')
    )) {
      event.stopImmediatePropagation();
      event.preventDefault();
      console.debug('已拦截ResizeObserver错误');
    }
  };
  
  // 添加错误监听器
  window.addEventListener('error', errorHandler, true);
  
  // 第二种解决方案：重写ResizeObserver类，添加debounce防抖
  // 这种方案更彻底地解决了问题根源
  const _ResizeObserver = window.ResizeObserver;
  window.ResizeObserver = class ResizeObserver extends _ResizeObserver {
    constructor(callback) {
      // 对回调函数进行200ms的防抖处理
      const debouncedCallback = debounce(callback, 200);
      super(debouncedCallback);
    }
  };
  
  console.log('ResizeObserver已被重写，添加了防抖功能');
  
  // 返回清理函数，便于在必要时移除监听器
  return () => {
    window.removeEventListener('error', errorHandler, true);
    // 注意：ResizeObserver的重写无法恢复
  };
}

/**
 * Vue组件中优化布局性能的指令
 * 可以注册为全局指令 v-optimize-layout
 */
export const optimizeLayoutDirective = {
  mounted(el) {
    // 添加CSS优化属性
    el.style.transform = 'translateZ(0)';
    el.style.backfaceVisibility = 'hidden';
    if (el.children && el.children.length > 5) {
      el.style.contain = 'content';
    }
  }
}; 