// 使用ES模块语法创建事件总线
class EventBus {
  constructor() {
    this.events = {};
  }

  on(eventName, fn) {
    if (!this.events[eventName]) {
      this.events[eventName] = [];
    }
    this.events[eventName].push(fn);
  }

  off(eventName, fn) {
    if (this.events[eventName]) {
      if (fn) {
        this.events[eventName] = this.events[eventName].filter(f => f !== fn);
      } else {
        delete this.events[eventName];
      }
    }
  }

  emit(eventName, data) {
    if (this.events[eventName]) {
      this.events[eventName].forEach(fn => fn(data));
    }
  }
}

// 创建单例并导出
const eventBus = new EventBus();
export default eventBus; 