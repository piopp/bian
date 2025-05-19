<template>
  <input
    :value="modelValue"
    @input="updateInput"
    v-bind="$attrs"
  />
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue';
import { debounce } from '../../utils/performance';

export default {
  name: 'DebouncedInput',
  inheritAttrs: false,
  props: {
    modelValue: {
      type: [String, Number],
      default: ''
    },
    // 防抖延迟时间，默认200ms
    debounceTime: {
      type: Number,
      default: 200
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    // 创建防抖版本的更新函数
    const debouncedUpdate = debounce((value) => {
      emit('update:modelValue', value);
    }, props.debounceTime);
    
    // 处理输入事件
    const updateInput = (e) => {
      const value = e.target.value;
      debouncedUpdate(value);
    };
    
    return {
      updateInput
    };
  }
};
</script>

<style scoped>
input {
  /* 避免输入时可能的闪烁 */
  transform: translateZ(0);
}
</style> 