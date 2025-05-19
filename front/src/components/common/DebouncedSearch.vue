<template>
  <div class="search-container" v-optimize-layout>
    <input
      type="text"
      class="search-input"
      :placeholder="placeholder"
      :value="modelValue"
      @input="updateSearch"
      v-bind="$attrs"
    />
    <span class="search-icon">🔍</span>
    <span v-if="modelValue" class="clear-icon" @click="clearSearch">×</span>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { debounce } from '../../utils/performance';

export default {
  name: 'DebouncedSearch',
  inheritAttrs: false,
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    placeholder: {
      type: String,
      default: '搜索...'
    },
    // 防抖延迟时间，默认300ms
    debounceTime: {
      type: Number,
      default: 300
    }
  },
  emits: ['update:modelValue', 'search'],
  setup(props, { emit }) {
    // 创建防抖版本的搜索更新函数
    const debouncedSearch = debounce((value) => {
      emit('update:modelValue', value);
      emit('search', value);
    }, props.debounceTime);
    
    // 处理输入变化
    const updateSearch = (e) => {
      const value = e.target.value;
      debouncedSearch(value);
    };
    
    // 清除搜索
    const clearSearch = () => {
      emit('update:modelValue', '');
      emit('search', '');
    };
    
    return {
      updateSearch,
      clearSearch
    };
  }
};
</script>

<style scoped>
.search-container {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  padding: 8px 32px 8px 30px;
  border: 1px solid #dcdee0;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
  transform: translateZ(0);
}

.search-input:focus {
  border-color: #1989fa;
  outline: none;
}

.search-icon {
  position: absolute;
  left: 8px;
  color: #909399;
  pointer-events: none;
}

.clear-icon {
  position: absolute;
  right: 8px;
  color: #909399;
  cursor: pointer;
  font-size: 16px;
}

.clear-icon:hover {
  color: #606266;
}
</style> 