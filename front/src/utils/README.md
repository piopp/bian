# 性能优化工具

本目录包含多种用于提升应用性能的工具，特别是解决界面交互和渲染问题，如ResizeObserver错误。

## 使用指南

### 防抖函数 (debounce)

防抖函数用于限制函数的执行频率，特别适用于处理输入、搜索和窗口调整等频繁变化的场景。

```js
import { debounce } from './utils/performance';

// 创建一个防抖处理的函数
const debouncedSearch = debounce((searchTerm) => {
  // 执行搜索逻辑
  api.search(searchTerm);
}, 300); // 300ms延迟

// 在输入事件中使用
function handleInput(e) {
  debouncedSearch(e.target.value);
}
```

### 节流函数 (throttle)

节流函数限制函数在一定时间内只能执行一次，适用于滚动事件或其他连续触发的事件。

```js
import { throttle } from './utils/performance';

// 创建一个节流处理的函数
const throttledScroll = throttle(() => {
  // 执行滚动处理逻辑
  updateScrollPosition();
}, 100); // 每100ms最多执行一次

// 在滚动事件中使用
window.addEventListener('scroll', throttledScroll);
```

### ResizeObserver错误处理

应用已在全局范围内处理了ResizeObserver错误，您不需要额外处理此类错误。

### 优化布局指令 (v-optimize-layout)

在需要优化渲染性能的组件上使用此指令：

```html
<template>
  <div v-optimize-layout>
    <!-- 包含大量动态内容或频繁更新的内容 -->
  </div>
</template>
```

### 预制组件

以下组件内置了防抖功能：

1. `DebouncedInput` - 带防抖功能的输入框
   ```html
   <DebouncedInput
     v-model="searchTerm"
     :debounce-time="300"
     placeholder="请输入搜索内容"
   />
   ```

2. `DebouncedSearch` - 带防抖功能的搜索框
   ```html
   <DebouncedSearch
     v-model="keyword"
     @search="performSearch"
     placeholder="搜索用户"
   />
   ```

## 最佳实践

1. 对于频繁触发的事件和用户输入，使用防抖或节流函数
2. 对于包含大量数据的组件，使用`v-optimize-layout`指令
3. 对于列表渲染，考虑使用虚拟滚动技术
4. 大型表单中使用`DebouncedInput`代替标准输入框 