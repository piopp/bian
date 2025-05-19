<template>
  <el-dialog
    title="万能划转"
    v-model="dialogVisible"
    width="600px"
    :close-on-click-modal="false"
    class="universal-transfer-dialog"
  >
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <p>在不同账户类型之间转移资产，支持子母账户间和账户类型间的划转。</p>
    </el-alert>
    
    <el-tabs v-model="activeTab">
      <el-tab-pane label="主账户内部划转" name="internal">
        <!-- 主账户内部账户类型之间的转账 -->
        <el-form
          ref="internalFormRef"
          :model="internalForm"
          :rules="internalRules"
          label-width="120px"
          label-position="right"
        >
          <el-form-item label="转出账户" prop="fromType">
            <el-select v-model="internalForm.fromType" placeholder="请选择转出账户类型" style="width: 100%">
              <el-option
                v-for="type in accountTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              ></el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="转入账户" prop="toType">
            <el-select v-model="internalForm.toType" placeholder="请选择转入账户类型" style="width: 100%">
              <el-option
                v-for="type in accountTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
                :disabled="type.value === internalForm.fromType"
              ></el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item 
            label="交易对" 
            prop="symbol"
            v-if="needsSymbol"
          >
            <el-input v-model="internalForm.symbol" placeholder="请输入交易对，如BTCUSDT"></el-input>
            <div class="form-tip">逐仓保证金账户转账必须指定交易对</div>
          </el-form-item>
          
          <el-form-item label="币种" prop="asset">
            <el-select v-model="internalForm.asset" placeholder="请选择币种" style="width: 100%">
              <el-option
                v-for="coin in commonCoins"
                :key="coin.value"
                :label="coin.label"
                :value="coin.value"
              ></el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="转账金额" prop="amount">
            <el-input v-model="internalForm.amount" type="number" placeholder="请输入转账金额">
              <template #append>{{ internalForm.asset }}</template>
            </el-input>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="子母账户划转" name="subaccount">
        <!-- 子母账户之间的转账 -->
        <el-form
          ref="subaccountFormRef"
          :model="subaccountForm"
          :rules="subaccountRules"
          label-width="120px"
          label-position="right"
        >
          <el-form-item label="转账方向" prop="direction">
            <el-radio-group v-model="subaccountForm.direction">
              <el-radio label="toSubaccount">母账户 -> 子账户</el-radio>
              <el-radio label="fromSubaccount">子账户 -> 母账户</el-radio>
              <el-radio label="subToSub">子账户 -> 子账户</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item 
            v-if="(subaccountForm.direction === 'fromSubaccount' || subaccountForm.direction === 'subToSub') && !subaccountForm.batchMode" 
            label="源子账户" 
            prop="fromEmail"
          >
            <el-select v-model="subaccountForm.fromEmail" placeholder="请选择源子账户" style="width: 100%" filterable>
              <el-option
                v-for="account in subaccounts"
                :key="account.email"
                :label="account.email"
                :value="account.email"
              ></el-option>
            </el-select>
          </el-form-item>

          <el-form-item 
            v-if="(subaccountForm.direction === 'toSubaccount' || subaccountForm.direction === 'subToSub') && !subaccountForm.batchMode" 
            label="目标子账户" 
            prop="toEmail"
          >
            <el-select v-model="subaccountForm.toEmail" placeholder="请选择目标子账户" style="width: 100%" filterable>
              <el-option
                v-for="account in subaccounts"
                :key="account.email"
                :label="account.email"
                :value="account.email"
                :disabled="account.email === subaccountForm.fromEmail"
              ></el-option>
            </el-select>
          </el-form-item>
          
          <!-- 批量模式复选框 -->
          <el-form-item 
            v-if="subaccountForm.direction === 'toSubaccount'" 
            label=""
          >
            <el-checkbox v-model="subaccountForm.batchMode">批量划转到多个子账户</el-checkbox>
          </el-form-item>
          
          <!-- 批量模式下的多选子账户 -->
          <el-form-item 
            v-if="subaccountForm.direction === 'toSubaccount' && subaccountForm.batchMode" 
            label="目标子账户" 
            prop="toEmails"
          >
            <el-select 
              v-model="subaccountForm.toEmails" 
              multiple 
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择多个目标子账户" 
              style="width: 100%" 
              filterable
            >
              <el-option
                v-for="account in subaccounts"
                :key="account.email"
                :label="account.email"
                :value="account.email"
              ></el-option>
            </el-select>
            <div class="form-tip">已选择 {{ subaccountForm.toEmails.length }} 个子账户</div>
          </el-form-item>
          
          <!-- 批量模式 - 对于 fromSubaccount 方向 -->
          <el-form-item 
            v-if="subaccountForm.direction === 'fromSubaccount'" 
            label=""
          >
            <el-checkbox v-model="subaccountForm.batchMode">批量从多个子账户划转</el-checkbox>
          </el-form-item>
          
          <!-- 批量模式下的多选子账户 (源账户) -->
          <el-form-item 
            v-if="subaccountForm.direction === 'fromSubaccount' && subaccountForm.batchMode" 
            label="源子账户" 
            prop="fromEmails"
          >
            <el-select 
              v-model="subaccountForm.fromEmails" 
              multiple 
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择多个源子账户" 
              style="width: 100%" 
              filterable
            >
              <el-option
                v-for="account in subaccounts"
                :key="account.email"
                :label="account.email"
                :value="account.email"
              ></el-option>
            </el-select>
            <div class="form-tip">已选择 {{ subaccountForm.fromEmails.length }} 个子账户</div>
          </el-form-item>
          
          <!-- 批量模式 - 对于 subToSub 方向 -->
          <el-form-item 
            v-if="subaccountForm.direction === 'subToSub'" 
            label=""
          >
            <el-checkbox v-model="subaccountForm.batchMode">批量子账户间划转</el-checkbox>
          </el-form-item>
          
          <!-- 批量模式下的多选子账户 (目标账户) - 仅用于 subToSub 方向 -->
          <el-form-item 
            v-if="subaccountForm.direction === 'subToSub' && subaccountForm.batchMode" 
            label="目标子账户" 
            prop="toEmails"
          >
            <el-select 
              v-model="subaccountForm.toEmails" 
              multiple 
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择多个目标子账户" 
              style="width: 100%" 
              filterable
            >
              <el-option
                v-for="account in subaccounts"
                :key="account.email"
                :label="account.email"
                :value="account.email"
                :disabled="subaccountForm.fromEmails && subaccountForm.fromEmails.includes(account.email)"
              ></el-option>
            </el-select>
            <div class="form-tip">已选择 {{ subaccountForm.toEmails.length }} 个子账户</div>
          </el-form-item>
          
          <el-form-item label="转出账户类型" prop="fromAccountType">
            <el-select v-model="subaccountForm.fromAccountType" placeholder="请选择转出账户类型" style="width: 100%">
              <el-option
                v-for="type in accountTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              ></el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="转入账户类型" prop="toAccountType">
            <el-select v-model="subaccountForm.toAccountType" placeholder="请选择转入账户类型" style="width: 100%">
              <el-option
                v-for="type in accountTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
                :disabled="type.value === subaccountForm.fromAccountType && subaccountForm.fromEmail === subaccountForm.toEmail"
              ></el-option>
            </el-select>
          </el-form-item>

          <el-form-item 
            label="交易对" 
            prop="symbol"
            v-if="subaccountNeedsSymbol"
          >
            <el-input v-model="subaccountForm.symbol" placeholder="请输入交易对，如BTCUSDT"></el-input>
            <div class="form-tip">逐仓保证金账户转账必须指定交易对</div>
          </el-form-item>
          
          <el-form-item label="币种" prop="asset">
            <el-select v-model="subaccountForm.asset" placeholder="请选择币种" style="width: 100%">
              <el-option
                v-for="coin in commonCoins"
                :key="coin.value"
                :label="coin.label"
                :value="coin.value"
              ></el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="转账金额" prop="amount">
            <el-input v-model="subaccountForm.amount" type="number" placeholder="请输入转账金额">
              <template #append>{{ subaccountForm.asset }}</template>
            </el-input>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="close">取消</el-button>
        <el-button 
          type="primary" 
          @click="executeTransfer" 
          :loading="loading"
        >
          {{ isActivateMode ? `批量激活账户 (${subaccountForm.toEmails.length}个)` : '执行划转' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCurrentUser, getAuthHeader } from '../../services/auth'

export default {
  name: 'UniversalTransferDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:visible', 'success'],
  setup(props, { emit }) {
    console.log('万能划转对话框组件初始化')
    
    // 加载状态
    const loading = ref(false)
    // 活动标签页
    const activeTab = ref('subaccount') // 默认选择子母账户划转
    // 子账户列表
    const subaccounts = ref([])
    // 表单引用
    const internalFormRef = ref(null)
    const subaccountFormRef = ref(null)
    
    // 激活模式标记
    const isActivateMode = ref(false)
    
    // 计算属性：对话框可见性，处理双向绑定
    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => {
        console.log('修改对话框可见性:', val);
        emit('update:visible', val);
        // 关闭对话框时重置激活模式
        if (!val) {
          isActivateMode.value = false
        }
      }
    })
    
    // 账户类型列表
    const accountTypes = [
      { label: '现货账户', value: 'SPOT' },
      { label: '杠杆账户', value: 'MARGIN' },
      { label: '逐仓杠杆账户', value: 'ISOLATED_MARGIN' },
      { label: '期货账户(U本位)', value: 'FUTURES' },
      { label: '期货账户(币本位)', value: 'COIN_FUTURES' },
      { label: '资金账户', value: 'FUNDING' }
    ]
    
    // 常用币种列表
    const commonCoins = [
      { label: 'USDT - 泰达币', value: 'USDT' },
      { label: 'BTC - 比特币', value: 'BTC' },
      { label: 'BNB - 币安币', value: 'BNB' },
      { label: 'ETH - 以太坊', value: 'ETH' },
      { label: 'SOL - 索拉纳', value: 'SOL' },
      { label: 'ADA - 艾达币', value: 'ADA' },
      { label: 'XRP - 瑞波币', value: 'XRP' },
      { label: 'DOGE - 狗狗币', value: 'DOGE' }
    ]
    
    // 主账户内部转账表单数据
    const internalForm = ref({
      fromType: 'SPOT',
      toType: 'FUTURES',
      asset: 'USDT',
      amount: '',
      symbol: ''
    })
    
    // 子母账户转账表单数据
    const subaccountForm = ref({
      direction: 'toSubaccount',
      fromEmail: '',
      toEmail: '',
      fromAccountType: 'SPOT',
      toAccountType: 'SPOT',
      asset: 'USDT',
      amount: '',
      symbol: '',
      batchMode: false,
      toEmails: [],
      fromEmails: []
    })
    
    // 关闭对话框
    const close = () => {
      dialogVisible.value = false;
      resetForms();
    };
    
    // 重置表单
    const resetForms = () => {
      if (internalFormRef.value) {
        internalFormRef.value.resetFields();
      }
      
      if (subaccountFormRef.value) {
        subaccountFormRef.value.resetFields();
      }
      
      // 重置批量模式和激活模式
      isActivateMode.value = false;
      
      // 重置表单数据到默认值
      internalForm.value = {
        fromType: 'SPOT',
        toType: 'MARGIN',
        symbol: '',
        asset: 'USDT',
        amount: ''
      };
      
      subaccountForm.value = {
        direction: 'toSubaccount',
        fromEmail: '',
        toEmail: '',
        fromAccountType: 'SPOT',
        toAccountType: 'SPOT',
        asset: 'USDT',
        amount: '',
        batchMode: false,
        toEmails: [],
        fromEmails: []
      };
    };
    
    // 监视转账类型变化，如果涉及逐仓保证金账户，则清空symbol字段
    watch([() => internalForm.value.fromType, () => internalForm.value.toType], () => {
      if (internalForm.value.fromType !== 'ISOLATED_MARGIN' && internalForm.value.toType !== 'ISOLATED_MARGIN') {
        internalForm.value.symbol = '';
      }
    });
    
    // 监视子账户转账类型变化
    watch([() => subaccountForm.value.fromAccountType, () => subaccountForm.value.toAccountType], () => {
      if (subaccountForm.value.fromAccountType !== 'ISOLATED_MARGIN' && subaccountForm.value.toAccountType !== 'ISOLATED_MARGIN') {
        subaccountForm.value.symbol = '';
      }
    });
    
    // 监视子账户转账方向变化
    watch(() => subaccountForm.value.direction, (newVal) => {
      if (newVal === 'toSubaccount') {
        subaccountForm.value.fromEmail = '';
      } else if (newVal === 'fromSubaccount') {
        subaccountForm.value.toEmail = '';
      }
      // 当方向变化时，重置批量模式
      subaccountForm.value.batchMode = false;
      subaccountForm.value.toEmails = [];
      subaccountForm.value.fromEmails = [];
    });

    // 监视批量模式变化
    watch(() => subaccountForm.value.batchMode, (newVal) => {
      if (newVal) {
        // 进入批量模式
        if (subaccountForm.value.direction === 'toSubaccount') {
          subaccountForm.value.toEmail = ''; // 清空单个目标账户
        } else if (subaccountForm.value.direction === 'fromSubaccount') {
          subaccountForm.value.fromEmail = ''; // 清空单个源账户
        }
      } else {
        // 退出批量模式
        subaccountForm.value.toEmails = [];
        subaccountForm.value.fromEmails = [];
      }
    });
    
    // 计算属性: 是否需要symbol参数（主账户内部转账）
    const needsSymbol = computed(() => {
      return internalForm.value.fromType === 'ISOLATED_MARGIN' || internalForm.value.toType === 'ISOLATED_MARGIN';
    });
    
    // 计算属性: 是否需要symbol参数（子母账户转账）
    const subaccountNeedsSymbol = computed(() => {
      return subaccountForm.value.fromAccountType === 'ISOLATED_MARGIN' || subaccountForm.value.toAccountType === 'ISOLATED_MARGIN';
    });
    
    // 主账户内部转账表单验证规则
    const internalRules = {
      fromType: [
        { required: true, message: '请选择转出账户类型', trigger: 'change' }
      ],
      toType: [
        { required: true, message: '请选择转入账户类型', trigger: 'change' },
        { validator: (rule, value, callback) => {
            if (value === internalForm.value.fromType) {
              callback(new Error('转入账户不能与转出账户相同'))
            } else {
              callback()
            }
          }, trigger: 'change' 
        }
      ],
      symbol: [
        { required: computed(() => needsSymbol.value), message: '使用逐仓保证金账户时必须提供交易对', trigger: 'blur' }
      ],
      asset: [
        { required: true, message: '请选择币种', trigger: 'change' }
      ],
      amount: [
        { required: true, message: '请输入转账金额', trigger: 'blur' },
        { 
          validator: (rule, value, callback) => {
            if (value === '') {
              callback(new Error('转账金额不能为空'))
            } else if (isNaN(Number(value)) || Number(value) <= 0) {
              callback(new Error('请输入大于0的有效金额'))
            } else {
              callback()
            }
          }, 
          trigger: 'blur' 
        }
      ]
    }
    
    // 子母账户转账表单验证规则
    const subaccountRules = {
      direction: [
        { required: true, message: '请选择转账方向', trigger: 'change' }
      ],
      fromEmail: [
        { 
          required: computed(() => 
            (subaccountForm.value.direction === 'fromSubaccount' || 
            subaccountForm.value.direction === 'subToSub') && 
            !subaccountForm.value.batchMode
          ), 
          message: '请选择源子账户', 
          trigger: 'change' 
        }
      ],
      toEmail: [
        { 
          required: computed(() => 
            (subaccountForm.value.direction === 'toSubaccount' || 
            subaccountForm.value.direction === 'subToSub') && 
            !subaccountForm.value.batchMode
          ), 
          message: '请选择目标子账户', 
          trigger: 'change' 
        }
      ],
      fromEmails: [
        {
          required: computed(() => 
            subaccountForm.value.direction === 'fromSubaccount' && 
            subaccountForm.value.batchMode
          ),
          validator: (rule, value, callback) => {
            if (subaccountForm.value.direction === 'fromSubaccount' && 
                subaccountForm.value.batchMode && 
                (!value || value.length === 0)) {
              callback(new Error('请至少选择一个源子账户'));
            } else {
              callback();
            }
          },
          trigger: 'change'
        }
      ],
      toEmails: [
        {
          required: computed(() => 
            subaccountForm.value.direction === 'toSubaccount' && 
            subaccountForm.value.batchMode
          ),
          validator: (rule, value, callback) => {
            if (subaccountForm.value.direction === 'toSubaccount' && 
                subaccountForm.value.batchMode && 
                (!value || value.length === 0)) {
              callback(new Error('请至少选择一个目标子账户'));
            } else {
              callback();
            }
          },
          trigger: 'change'
        }
      ],
      fromAccountType: [
        { required: true, message: '请选择转出账户类型', trigger: 'change' }
      ],
      toAccountType: [
        { required: true, message: '请选择转入账户类型', trigger: 'change' }
      ],
      symbol: [
        { 
          required: computed(() => subaccountNeedsSymbol.value), 
          message: '使用逐仓杠杆账户时必须提供交易对', 
          trigger: 'blur' 
        }
      ],
      asset: [
        { required: true, message: '请选择币种', trigger: 'change' }
      ],
      amount: [
        { required: true, message: '请输入转账金额', trigger: 'blur' },
        { 
          validator: (rule, value, callback) => {
            if (value === '') {
              callback(new Error('转账金额不能为空'))
            } else if (isNaN(Number(value)) || Number(value) <= 0) {
              callback(new Error('请输入大于0的有效金额'))
            } else {
              callback()
            }
          }, 
          trigger: 'blur' 
        }
      ]
    }
    
    // 获取账户类型标签
    const getAccountTypeLabel = (type) => {
      const found = accountTypes.find(t => t.value === type);
      return found ? found.label : type;
    }
    
    // 监视对话框可见性
    watch(() => props.visible, (newVal) => {
      console.log('UniversalTransferDialog - visible变更为:', newVal)
      if (newVal) {
        // 重置表单并加载数据
        console.log('对话框显示 - 重置表单并加载数据')
        resetForms()
        loadSubaccounts()
      }
    }, { immediate: true })
    
    // 加载子账户列表
    const loadSubaccounts = async () => {
      try {
        const user = getCurrentUser();
        if (!user || !user.token) {
          console.error('未找到当前用户或token');
          return;
        }
        
        const response = await fetch('/api/subaccounts/', {
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        });
        const result = await response.json();
        
        if (result.success && result.data && result.data.subaccounts) {
          subaccounts.value = result.data.subaccounts;
          console.log('子账户列表加载成功，数量:', subaccounts.value.length);
        } else {
          ElMessage.warning('获取子账户列表失败，部分功能可能受限');
          subaccounts.value = [];
        }
      } catch (error) {
        console.error('加载子账户列表异常:', error);
        ElMessage.error('加载子账户列表异常，请重试');
        subaccounts.value = [];
      }
    };
    
    // 执行划转操作
    const executeTransfer = () => {
      if (activeTab.value === 'internal') {
        // 主账户内部划转
        handleInternalTransfer();
      } else {
        // 子母账户划转
        if (isActivateMode.value) {
          // 批量激活模式
          handleActivateTransfer();
        } else {
          // 普通子母账户划转
          handleSubaccountTransfer();
        }
      }
    };
    
    // 批量激活账号转账处理
    const handleActivateTransfer = () => {
      subaccountFormRef.value.validate(async (valid) => {
        if (!valid) return;
        
        if (!subaccountForm.value.toEmails || subaccountForm.value.toEmails.length === 0) {
          ElMessage.warning('请选择至少一个子账号');
          return;
        }
        
        try {
          // 确认信息
          const confirmMessage = `确认要批量激活 ${subaccountForm.value.toEmails.length} 个子账号，从主账号 ${getAccountTypeLabel(subaccountForm.value.fromAccountType)} 向每个子账号的 ${getAccountTypeLabel(subaccountForm.value.toAccountType)} 各转入 ${subaccountForm.value.amount} ${subaccountForm.value.asset}？`;
          
          await ElMessageBox.confirm(
            confirmMessage,
            '批量激活账户确认',
            {
              confirmButtonText: '确认激活',
              cancelButtonText: '取消',
              type: 'warning'
            }
          );
          
          loading.value = true;
          
          // 构建批量转账请求
          const transfers = [];
          
          // 对每个选中的子账号
          for (const email of subaccountForm.value.toEmails) {
            transfers.push({
              fromAccountType: subaccountForm.value.fromAccountType,
              toAccountType: subaccountForm.value.toAccountType,
              fromEmail: '',  // 主账号不需要指定email
              toEmail: email,
              asset: subaccountForm.value.asset,
              amount: subaccountForm.value.amount,
              transferType: 'MAIN_UMFUTURE'  // 从主账号现货到子账号杠杆的转账类型
            });
          }
          
          // 批量执行转账时添加错误处理和超时控制
          try {
            // 添加请求超时控制
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000); // 批量操作可能需要更长时间，设为60秒
            
            const batchResponse = await fetch('/api/subaccounts/batch-transfer', {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              ...getAuthHeader()
            },
              body: JSON.stringify({ transfers }),
              signal: controller.signal
          });
            
            clearTimeout(timeoutId);
          
          const batchResult = await batchResponse.json();
            console.log('批量转账响应:', batchResult);
            
            // 详细记录失败案例
            if (!batchResult.success) {
              console.error('批量转账返回错误:', batchResult.error, '完整响应:', batchResult);
            } else if (batchResult.failed_transfers && batchResult.failed_transfers.length > 0) {
              console.warn('部分转账失败:', batchResult.failed_transfers);
            }
            
            // 检查API响应成功状态
            if (batchResponse.ok && batchResult.success) {
            // 关闭对话框并重置
            dialogVisible.value = false;
            resetForms();
            
            const successCount = batchResult.success_count || 0;
            const failCount = batchResult.fail_count || 0;
            
            if (successCount === transfers.length) {
              ElMessage.success(`成功激活 ${successCount} 个子账号`);
            } else if (successCount > 0) {
                // 使用通知框提供详细信息
                ElMessageBox.alert(
                  `部分账号激活成功: ${successCount}个成功, ${failCount}个失败\n\n${
                    batchResult.failed_transfers ? 
                    '失败详情:\n' + batchResult.failed_transfers.map(ft => 
                      `· ${ft.email || '未知账号'}: ${ft.error || '未知错误'}`
                    ).join('\n') : 
                    '未返回详细失败信息'
                  }`,
                  '批量激活结果',
                  {
                    type: 'warning',
                    confirmButtonText: '确定'
                  }
                );
            } else {
                ElMessageBox.alert(
                  `所有账号激活都失败了\n\n${
                    batchResult.failed_transfers ? 
                    '失败详情:\n' + batchResult.failed_transfers.map(ft => 
                      `· ${ft.email || '未知账号'}: ${ft.error || '未知错误'}`
                    ).join('\n') : 
                    '未返回详细失败信息'
                  }`,
                  '批量激活失败',
                  {
                    type: 'error',
                    confirmButtonText: '确定'
                  }
                );
            }
            
            // 通知父组件
            emit('success', {
              type: 'batch-activate',
              accounts: transfers.length,
              success: successCount,
                failed: failCount,
                failedDetails: batchResult.failed_transfers || []
            });
          } else {
              // 处理不同类型的错误
              let errorMsg = batchResult.error || '批量激活账户失败，请重试';
              
              // 解析特定的API错误
              if (errorMsg.includes('type') && errorMsg.includes('not sent')) {
                errorMsg = '激活失败：缺少必要参数类型。请联系技术支持。';
              } else if (errorMsg.includes('timestamp')) {
                errorMsg = '激活失败：服务器时间同步问题。请重试。';
              } else if (errorMsg.includes('balance') || errorMsg.includes('insufficient')) {
                errorMsg = '激活失败：主账号余额不足，无法执行转账。';
              }
              
              // 使用警告框显示更详细的错误信息
              ElMessageBox.alert(
                `批量激活请求失败: ${errorMsg}`,
                '批量激活错误',
                {
                  type: 'error',
                  confirmButtonText: '确定'
                }
              );
            }
          } catch (fetchError) {
            // 处理网络请求本身的错误
            console.error('批量激活网络请求错误:', fetchError);
            
            let networkErrorMsg = '网络请求失败';
            if (fetchError.name === 'AbortError') {
              networkErrorMsg = '请求超时，请检查网络连接后重试';
            }
            
            ElMessage.error(networkErrorMsg);
          }
        } catch (error) {
          if (error !== 'cancel') {
            ElMessage.error('操作取消或出现异常');
            console.error('批量激活出错:', error);
          }
        } finally {
          loading.value = false;
        }
      });
    };
    
    // 主账户内部转账逻辑
    const handleInternalTransfer = () => {
      console.log('开始处理主账户内部转账逻辑');
      
      internalFormRef.value.validate(async (valid) => {
        if (!valid) return false;
        
        try {
          // 二次确认
          await ElMessageBox.confirm(
            `确认要从${getAccountTypeLabel(internalForm.value.fromType)}转出 ${internalForm.value.amount} ${internalForm.value.asset} 到${getAccountTypeLabel(internalForm.value.toType)}?`,
            '转账确认',
            {
              confirmButtonText: '确认转账',
              cancelButtonText: '取消',
              type: 'warning'
            }
          );
          
          loading.value = true;
          
          // 准备转账参数
          const transferData = {
            asset: internalForm.value.asset,
            amount: internalForm.value.amount,
            from_type: internalForm.value.fromType,
            to_type: internalForm.value.toType
          };
          
          // 如果需要交易对参数，则添加
          if (needsSymbol.value) {
            transferData.symbol = internalForm.value.symbol;
          }
          
          // 调用API并处理响应
          try {
            // 添加请求超时控制
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时
            
          const response = await fetch('/api/subaccounts/internal-transfer', {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              ...getAuthHeader()
            },
              body: JSON.stringify(transferData),
              signal: controller.signal
          });
            
            clearTimeout(timeoutId);
          
          const result = await response.json();
            console.log('内部转账响应:', result);
            
            // 详细记录API返回的结果
            if (!result.success) {
              console.error('内部转账API返回错误:', result.error, '完整响应:', result);
            }
            
            // 检查API响应成功状态 - 确保同时检查HTTP状态和JSON中的success字段
            if (response.ok && result.success) {
            // 关闭对话框并清空表单
            dialogVisible.value = false;
            
            // 触发成功事件
            emit('success', {
              type: 'internal',
              from: internalForm.value.fromType,
              to: internalForm.value.toType,
              asset: internalForm.value.asset,
              amount: internalForm.value.amount
            });
            
            ElMessage.success(`转账成功！已将 ${internalForm.value.amount} ${internalForm.value.asset} 从${getAccountTypeLabel(internalForm.value.fromType)}转入${getAccountTypeLabel(internalForm.value.toType)}`);
          } else {
              // 处理不同类型的错误
              let errorMsg = result.error || '转账失败，请重试';
              
              // 分析并显示更具体的错误信息
              if (errorMsg.includes('type') && errorMsg.includes('not sent') || 
                  errorMsg.includes('not sent, was empty/null, or malformed')) {
                errorMsg = '转账失败：缺少必要参数类型。请联系技术支持。';
              } else if (errorMsg.includes('timestamp')) {
                errorMsg = '转账失败：服务器时间同步问题。请重试。';
              } else if (errorMsg.includes('account')) {
                errorMsg = '转账失败：账户参数错误或账户状态异常。';
              } else if (errorMsg.includes('balance') || errorMsg.includes('insufficient')) {
                errorMsg = '转账失败：账户余额不足。';
              }
              
              // 使用警告框显示更详细的错误信息
              ElMessageBox.alert(
                `请求失败: ${errorMsg}`,
                '内部转账错误',
                {
                  type: 'error',
                  confirmButtonText: '确定',
                  callback: () => {
                    console.log('用户确认了错误提示');
                  }
                }
              );
            }
          } catch (fetchError) {
            // 处理网络请求本身的错误
            console.error('内部转账网络请求错误:', fetchError);
            
            let networkErrorMsg = '网络请求失败';
            if (fetchError.name === 'AbortError') {
              networkErrorMsg = '请求超时，请检查网络连接后重试';
            }
            
            ElMessage.error(networkErrorMsg);
          }
        } catch (error) {
          if (error !== 'cancel') {
            ElMessage.error('操作取消或出现异常');
            console.error('内部转账出错:', error);
          }
        } finally {
          loading.value = false;
        }
      });
    };
    
    // 子母账户转账逻辑
    const handleSubaccountTransfer = () => {
      console.log('开始处理子母账户转账逻辑');
      
      subaccountFormRef.value.validate(async (valid) => {
        if (!valid) {
          console.error('表单验证失败');
          return false;
        }
        
        try {
          // 获取当前用户信息
          const currentUser = getCurrentUser();
          const userId = currentUser ? currentUser.userId || currentUser.id : '';
          
          // 准备确认信息
          let confirmMessage = '';
          
          // 根据是否批量模式和转账方向构建不同的确认消息
          if (subaccountForm.value.batchMode) {
            if (subaccountForm.value.direction === 'toSubaccount') {
              const targetCount = subaccountForm.value.toEmails.length;
              confirmMessage = `确认要从母账户${getAccountTypeLabel(subaccountForm.value.fromAccountType)}批量转出 ${subaccountForm.value.amount} ${subaccountForm.value.asset} 到${targetCount}个子账户的${getAccountTypeLabel(subaccountForm.value.toAccountType)}?`;
            } else if (subaccountForm.value.direction === 'fromSubaccount') {
              const sourceCount = subaccountForm.value.fromEmails.length;
              confirmMessage = `确认要从${sourceCount}个子账户的${getAccountTypeLabel(subaccountForm.value.fromAccountType)}批量转出 ${subaccountForm.value.amount} ${subaccountForm.value.asset} 到母账户${getAccountTypeLabel(subaccountForm.value.toAccountType)}?`;
            }
          } else {
            // 非批量模式的确认消息
            if (subaccountForm.value.direction === 'toSubaccount') {
              confirmMessage = `确认要从母账户${getAccountTypeLabel(subaccountForm.value.fromAccountType)}转出 ${subaccountForm.value.amount} ${subaccountForm.value.asset} 到子账户${subaccountForm.value.toEmail}的${getAccountTypeLabel(subaccountForm.value.toAccountType)}?`;
            } else if (subaccountForm.value.direction === 'fromSubaccount') {
              confirmMessage = `确认要从子账户${subaccountForm.value.fromEmail}的${getAccountTypeLabel(subaccountForm.value.fromAccountType)}转出 ${subaccountForm.value.amount} ${subaccountForm.value.asset} 到母账户${getAccountTypeLabel(subaccountForm.value.toAccountType)}?`;
            } else {
              confirmMessage = `确认要从子账户${subaccountForm.value.fromEmail}的${getAccountTypeLabel(subaccountForm.value.fromAccountType)}转出 ${subaccountForm.value.amount} ${subaccountForm.value.asset} 到子账户${subaccountForm.value.toEmail}的${getAccountTypeLabel(subaccountForm.value.toAccountType)}?`;
            }
          }
          
          // 二次确认
          await ElMessageBox.confirm(
            confirmMessage,
            '转账确认',
            {
              confirmButtonText: '确认转账',
              cancelButtonText: '取消',
              type: 'warning'
            }
          );
          
          loading.value = true;
          
          // 准备划转参数，根据不同的模式构建不同的请求
          let transferData = {
            user_id: userId,
            asset: subaccountForm.value.asset,
            amount: subaccountForm.value.amount,
            fromAccountType: subaccountForm.value.fromAccountType,
            toAccountType: subaccountForm.value.toAccountType
          };
          
          // 如果需要交易对参数，则添加
          if (subaccountNeedsSymbol.value) {
            transferData.symbol = subaccountForm.value.symbol;
          }
          
          // 根据转账方向和批量模式设置不同的参数
          if (subaccountForm.value.batchMode) {
            if (subaccountForm.value.direction === 'toSubaccount') {
              // 批量从母账户到多个子账户
              transferData.toEmails = subaccountForm.value.toEmails;
            } else if (subaccountForm.value.direction === 'fromSubaccount') {
              // 批量从多个子账户到母账户
              transferData.fromEmails = subaccountForm.value.fromEmails;
              // 确保设置正确的转账类型
              transferData.transferType = 'SUB_MAIN';
            }
          } else {
            // 非批量模式
            if (subaccountForm.value.direction === 'toSubaccount') {
              transferData.toEmail = subaccountForm.value.toEmail;
              transferData.transferType = 'MAIN_SUB';
            } else if (subaccountForm.value.direction === 'fromSubaccount') {
              transferData.fromEmail = subaccountForm.value.fromEmail;
              transferData.transferType = 'SUB_MAIN';
            } else {
              transferData.fromEmail = subaccountForm.value.fromEmail;
              transferData.toEmail = subaccountForm.value.toEmail;
              transferData.transferType = 'SUB_SUB';
            }
          }
          
          // 创建clientTranId以追踪交易
          transferData.clientTranId = `${new Date().getTime()}_${Math.floor(Math.random() * 1000)}`;
          
          console.log('发送万能划转请求:', transferData);
          
          // 调用API
          try {
            // 添加请求超时控制
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时
            
          const response = await fetch('/api/subaccounts/universal-transfer', {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${currentUser.token}`
            },
              body: JSON.stringify(transferData),
              signal: controller.signal
          });
            
            clearTimeout(timeoutId);
          
          const result = await response.json();
          console.log('万能划转响应:', result);
          
            // 详细记录API返回的结果
            if (!result.success) {
              console.error('API返回错误:', result.error, '完整响应:', result);
            }
            
            // 检查API响应成功状态
            if (response.ok && result.success) {
            // 关闭对话框并清空表单
            dialogVisible.value = false;
            
            // 触发成功事件
            emit('success', {
              type: 'universal',
              ...transferData
            });
            
            // 根据批量模式展示不同的成功消息
            if (subaccountForm.value.batchMode) {
              const successCount = result.data?.success_count || 0;
              const totalCount = result.data?.total || 0;
              ElMessage.success(`批量划转已完成！成功: ${successCount}/${totalCount} 笔`);
            } else {
              ElMessage.success('转账已成功执行！');
            }
          } else {
              // 处理不同类型的错误
              let errorMsg = result.error || '转账失败，请重试';
              
              // 解析特定的API错误
              if (errorMsg.includes('type') && errorMsg.includes('not sent') || 
                  errorMsg.includes('not sent, was empty/null, or malformed')) {
                errorMsg = '转账失败：缺少必要参数类型。请联系技术支持。';
              } else if (errorMsg.includes('timestamp')) {
                errorMsg = '转账失败：服务器时间同步问题。请重试。';
              } else if (errorMsg.includes('account')) {
                errorMsg = '转账失败：账户参数错误或账户状态异常。';
              } else if (errorMsg.includes('balance') || errorMsg.includes('insufficient')) {
                errorMsg = '转账失败：账户余额不足。';
              }
              
              // 使用警告框显示更详细的错误信息
              ElMessageBox.alert(
                `请求失败: ${errorMsg}`,
                '划转错误',
                {
                  type: 'error',
                  confirmButtonText: '确定'
                }
              );
            }
          } catch (fetchError) {
            // 处理网络请求本身的错误
            console.error('划转网络请求错误:', fetchError);
            
            let networkErrorMsg = '网络请求失败';
            if (fetchError.name === 'AbortError') {
              networkErrorMsg = '请求超时，请检查网络连接后重试';
            }
            
            ElMessage.error(networkErrorMsg);
          }
        } catch (error) {
          if (error !== 'cancel') {
            ElMessage.error('操作取消或出现异常');
            console.error('万能划转出错:', error);
          }
        } finally {
          loading.value = false;
        }
      });
    };
    
    // 监听批量激活事件
    onMounted(() => {
      const handleActivateAccounts = (event) => {
        const { accounts, fromType, toType, isBatchActivate, asset, defaultAmount } = event.detail;
        
        if (isBatchActivate && accounts && accounts.length > 0) {
          isActivateMode.value = true;
          activeTab.value = 'subaccount';
          
          // 设置为批量模式，从主账号到子账号
          subaccountForm.value.direction = 'toSubaccount';
          subaccountForm.value.batchMode = true;
          subaccountForm.value.fromAccountType = fromType || 'SPOT';
          subaccountForm.value.toAccountType = toType || 'MARGIN';
          
          // 设置选中的子账号
          subaccountForm.value.toEmails = accounts.map(acc => acc.email);
          
          // 设置默认资产和金额
          subaccountForm.value.asset = asset || 'USDT';
          subaccountForm.value.amount = defaultAmount ? defaultAmount.toString() : '50';
          
          // 更新对话框标题
          setTimeout(() => {
            const dialogHeader = document.querySelector('.universal-transfer-dialog .el-dialog__title');
            if (dialogHeader) {
              dialogHeader.textContent = '批量激活账户';
            }
          }, 50);
        }
      };
      
      window.addEventListener('activate-accounts', handleActivateAccounts);
      
      // 组件卸载时移除事件监听
      onUnmounted(() => {
        window.removeEventListener('activate-accounts', handleActivateAccounts);
      });
    });
    
    return {
      activeTab,
      dialogVisible,
      internalForm,
      subaccountForm,
      internalFormRef,
      subaccountFormRef,
      commonCoins,
      accountTypes,
      loading,
      subaccounts,
      executeTransfer,
      needsSymbol,
      getAccountTypeLabel,
      close,
      isActivateMode,
      internalRules,
      subaccountRules
    }
  }
}
</script>

<style scoped>
.universal-transfer-dialog :deep(.el-dialog__body) {
  padding-top: 10px;
}

.form-tip {
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
  margin-top: 5px;
}

.account-type-tag {
  display: inline-block;
  margin-right: 5px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style> 