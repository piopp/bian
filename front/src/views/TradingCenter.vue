<template>
  <div class="trading-center-container">
    <div class="row mb-3">
      <div class="col-12">
        <div class="d-flex align-items-center justify-content-between">
          <h4 class="mb-0">交易中心</h4>
          
          <!-- 全局查询设置 -->
          <div class="global-query-settings d-flex align-items-center">
            <div class="setting-item">
              <span class="me-2">查询起始时间:</span>
              <el-date-picker
                v-model="queryStartTime"
                type="datetime"
                placeholder="选择起始时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="x"
                style="width: 220px"
                :clearable="false"
              />
              <el-button type="primary" size="small" class="ms-2" @click="resetQueryStartTime">
                重置为登录时间
              </el-button>
            </div>
            <div class="setting-item ms-4">
              <span class="me-2">全局交易对:</span>
              <el-select
                v-model="globalSymbol"
                filterable
                placeholder="选择交易对"
                style="width: 150px"
                clearable
                @change="handleGlobalSymbolChange"
              >
                <el-option
                  v-for="pair in tradingPairs"
                  :key="pair.value"
                  :label="pair.label"
                  :value="pair.value"
                />
              </el-select>
            </div>
            <div class="setting-item ms-4">
              <span class="me-2">合约类型:</span>
              <el-radio-group v-model="contractType" size="small" @change="handleContractTypeChange">
                <el-radio-button label="UM">U本位</el-radio-button>
                <el-radio-button label="CM">币本位</el-radio-button>
              </el-radio-group>
            </div>
            <div class="setting-item ms-4">
              <span class="me-2">刷新间隔:</span>
              <el-select v-model="globalRefreshInterval" style="width: 100px" @change="handleRefreshIntervalChange">
                <el-option :value="1" label="1秒" />
                <el-option :value="3" label="3秒" />
                <el-option :value="5" label="5秒" />
                <el-option :value="10" label="10秒" />
                <el-option :value="30" label="30秒" />
                <el-option :value="60" label="1分钟" />
                </el-select>
            </div>
            <div class="setting-item ms-4">
              <el-button type="primary" size="small" @click="refreshAllData">
                立即刷新数据
                </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="account-selection-card">
          <template #header>
            <div class="card-header">
              <span>子账号选择</span>
              <el-button type="primary" @click="refreshSubaccounts">刷新列表</el-button>
            </div>
          </template>
          
          <div class="filter-container">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索子账号"
              clearable
              class="filter-input"
            />
            <div class="selection-actions">
              <el-button 
                type="primary" 
                @click="selectAll" 
                :disabled="filteredSubaccounts.length === 0"
              >
                全选
              </el-button>
              <el-button 
                type="info" 
                @click="deselectAll" 
                :disabled="selectedAccounts.length === 0"
              >
                取消全选
              </el-button>
            </div>
          </div>
          
          <el-table
            ref="subaccountTable"
            :data="filteredSubaccounts"
            @selection-change="handleSelectionChange"
            style="width: 100%"
            max-height="400px"
            :row-key="row => row.email"
          >
            <el-table-column type="selection" width="55" :selectable="checkSelectable" />
            <el-table-column prop="email" label="子账号邮箱" min-width="180" />
            <el-table-column prop="api_key_status" label="API状态" width="100">
              <template #default="scope">
                <el-tag 
                  :type="scope.row.has_api_key ? 'success' : 'danger'"
                >
                  {{ scope.row.has_api_key ? '已配置' : '未配置' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="scope">
                <div class="action-buttons">
                  <el-button 
                    size="small" 
                    type="primary" 
                    @click="viewAccountDetails(scope.row)"
                    :disabled="!scope.row.has_api_key"
                  >
                    详情
                  </el-button>
                  <el-dropdown>
                    <el-button size="small" type="info">
                      更多操作<i class="el-icon-arrow-down el-icon--right"></i>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item 
                          @click="openAutoArbitrage(scope.row)"
                          :disabled="!scope.row.has_api_key"
                        >套利</el-dropdown-item>
                        <el-dropdown-item 
                          @click="openGridTrading(scope.row)"
                          :disabled="!scope.row.has_api_key"
                        >网格</el-dropdown-item>
                        <el-dropdown-item 
                          @click="openPositionModeSettings(scope.row)"
                          :disabled="!scope.row.has_api_key"
                        >持仓模式</el-dropdown-item>
                        <el-dropdown-item 
                          @click="handleAutoCollection(scope.row)"
                          :disabled="!scope.row.has_api_key"
                        >资金归集</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card class="batch-actions-card">
          <template #header>
            <div class="card-header">
              <span>批量操作 (已选择 {{ selectedAccounts.length }} 个子账号)</span>
            </div>
          </template>
          
          <div class="batch-buttons">
            <el-button 
              type="success" 
              @click="batchAutoArbitrage" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-money"
            >
              批量套利交易
            </el-button>
            <el-button 
              type="warning" 
              @click="batchGridTrading" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-s-grid"
            >
              批量网格建仓
            </el-button>
            <el-button 
              type="info" 
              @click="batchMarginDetails" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-s-data"
            >
              杠杆账户详情
            </el-button>
            
            <el-button 
              type="primary" 
              @click="batchPositionModeSettings" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-set-up"
            >
              批量设置持仓模式
            </el-button>
            
            <el-button 
              type="success" 
              @click="batchSetLeverage" 
              :disabled="selectedAccounts.length === 0 || !globalSymbol"
              icon="el-icon-setting"
            >
              批量设置杠杆
            </el-button>

            <el-button 
              type="danger" 
              @click="batchAutoCollection" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-coin"
            >
              批量资金归集
            </el-button>
            
            <el-button 
              type="warning" 
              @click="batchSetRepayMode" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-money"
            >
              批量设置还款模式
            </el-button>
            
            <el-button 
              type="info" 
              @click="batchGetRepayMode" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-search"
            >
              批量查询还款模式
            </el-button>
            
            <el-button 
              type="danger" 
              @click="batchFuturesRepay" 
              :disabled="selectedAccounts.length === 0"
              icon="el-icon-wallet"
            >
              批量执行还款
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 持仓展示区 -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>子账号持仓列表</span>
            </div>
          </template>
          <position-list 
            ref="positionListRef"
            :positions="positions" 
            :subaccounts="selectedAccounts" 
            :queryStartTime="queryStartTime" 
            :globalSymbol="globalSymbol" 
            :contractType="contractType"
            :refreshInterval="globalRefreshInterval * 1000"
            @batch-close="openBatchCloseDialog" 
            @system-message="handleChildMessage"
          />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 限价单列表 -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>挂单列表</span>
            </div>
          </template>
          <limit-order-list 
            ref="limitOrderListRef"
            :orders="orders" 
            :subaccounts="selectedAccounts" 
            :queryStartTime="queryStartTime" 
            :globalSymbol="globalSymbol" 
            :contractType="contractType"
            :refreshInterval="globalRefreshInterval * 1000"
            @system-message="handleChildMessage"
          />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 历史订单查询区域 -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>历史订单查询</span>
              <div class="header-actions">
                <el-button-group>
                  <el-button type="primary" size="small" :class="{ 'active-tab': activeTab === 'trades' }" @click="activeTab = 'trades'">合约成交记录</el-button>
                  <el-button type="primary" size="small" :class="{ 'active-tab': activeTab === 'margin' }" @click="activeTab = 'margin'">杠杆成交记录</el-button>
                </el-button-group>
              </div>
            </div>
          </template>
          <trade-history-list 
            v-if="activeTab === 'trades'" 
            ref="tradeHistoryListRef"
            :subaccounts="selectedAccounts" 
            :queryStartTime="queryStartTime" 
            :globalSymbol="globalSymbol" 
            :contractType="contractType"
            :refreshInterval="globalRefreshInterval * 1000"
            :positionVersion="positionVersion"
            @system-message="handleChildMessage"
          />
          <margin-trade-history 
            v-else-if="activeTab === 'margin'" 
            :subaccounts="selectedAccounts" 
            :queryStartTime="queryStartTime" 
            :globalSymbol="globalSymbol" 
            :refreshInterval="10000"
            @system-message="handleChildMessage"
          />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 引入交易费用统计悬浮组件 -->
    <trade-fees-summary :subaccounts="selectedAccounts" :queryStartTime="queryStartTime" :activeTab="activeTab" :globalSymbol="globalSymbol" :contractType="contractType" />
    
    <!-- 消息窗口悬浮按钮 -->
    <div class="message-icon-container" v-if="systemMessages.length > 0" @click="showMessageWindow = true">
      <el-badge :value="systemMessages.length" :max="99" type="danger">
        <el-button type="primary" circle icon="el-icon-bell"></el-button>
      </el-badge>
    </div>
    
    <!-- 添加消息通知窗口，悬浮在手续费下方 -->
    <div class="message-window-container" v-show="showMessageWindow">
      <div class="message-window">
        <div class="message-window-header">
          <span>系统通知</span>
          <div class="message-window-controls">
            <el-button type="text" @click="clearMessages" size="small">清空</el-button>
            <el-button type="text" @click="showMessageWindow = false" size="small">关闭</el-button>
          </div>
        </div>
        <div class="message-window-body">
          <div class="message-list">
            <div class="message-item" v-for="(message, index) in systemMessages" :key="index">
              <el-alert
                :type="message.type"
                :title="message.title"
                :description="message.description"
                :closable="false"
                show-icon
              />
            </div>
          </div>
          <div v-if="systemMessages.length === 0" class="no-messages">
            暂无消息通知
          </div>
        </div>
      </div>
    </div>
    
    <!-- 组件运行状态悬浮框 -->
    <div class="component-status-container" v-show="showComponentStatus">
      <div class="component-status-window">
        <div class="component-status-header">
          <span>组件运行状态</span>
          <div class="component-status-controls">
            <el-button type="text" @click="showComponentStatus = false" size="small">关闭</el-button>
          </div>
        </div>
        <div class="component-status-body">
          <el-table :data="componentStatusList" style="width: 100%" size="small">
            <el-table-column prop="component" label="组件名称" width="150"></el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === '正常' ? 'success' : scope.row.status === '警告' ? 'warning' : 'danger'">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="lastUpdate" label="最后更新" width="180"></el-table-column>
            <el-table-column prop="message" label="状态消息"></el-table-column>
          </el-table>
        </div>
      </div>
    </div>
    
    <!-- 组件状态悬浮按钮 -->
    <div class="component-status-icon-container" @click="showComponentStatus = true">
      <el-badge v-if="abnormalComponentCount > 0" :value="abnormalComponentCount" :max="99" type="danger">
        <el-button :type="abnormalComponentCount > 0 ? 'danger' : 'success'" circle icon="el-icon-monitor"></el-button>
      </el-badge>
      <el-button v-else type="success" circle icon="el-icon-monitor"></el-button>
    </div>
    
    <!-- 缓存状态显示组件 -->
    <div class="cache-status-container" v-if="showCacheInfo">
      <div class="cache-status-window">
        <div class="cache-status-header">
          <span>数据缓存状态</span>
          <div class="cache-status-controls">
            <el-button type="text" @click="handleClearCache" size="small">清除缓存</el-button>
            <el-button type="text" @click="showCacheInfo = false" size="small">关闭</el-button>
          </div>
        </div>
        <div class="cache-status-body">
          <div class="cache-info">
            <p><strong>缓存状态:</strong> {{ cacheStatus.hasCache ? '已缓存' : '未缓存' }}</p>
            <p><strong>缓存大小:</strong> {{ cacheStatus.cacheSize }} 条</p>
            <p><strong>最后更新:</strong> {{ cacheStatus.lastUpdate ? new Date(cacheStatus.lastUpdate).toLocaleString() : '未更新' }}</p>
          </div>
          <div class="cache-description">
            <p>系统已启用交易数据共享缓存，减少重复请求。手续费查询与交易历史共用同一份数据。</p>
            <p>缓存默认有效期为30秒，自动刷新时使用缓存数据，手动刷新时获取最新数据。</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 缓存状态悬浮按钮 -->
    <div class="cache-icon-container" @click="showCacheInfo = true">
      <el-badge :value="cacheStatus.cacheSize || 0" :max="99" :hidden="!cacheStatus.hasCache">
        <el-button :type="cacheStatus.hasCache ? 'success' : 'info'" circle icon="el-icon-coin"></el-button>
      </el-badge>
    </div>
    
    <!-- 组件对话框 -->
    <auto-arbitrage-dialog
      v-model="showAutoArbitrageDialog"
      :account="currentAccount"
      :selectedAccounts="isBatchMode ? selectedAccounts : []"
      @success="handleArbitrageSuccess"
    />
    
    <!-- 持仓模式设置对话框 -->
    <el-dialog
      v-model="positionModeVisible"
      title="设置持仓模式"
      width="500px"
    >
      <div v-if="currentAccount">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          class="mb-4"
        >
          <p>为账号 {{ currentAccount.email }} 设置U本位合约持仓模式</p>
          <p>单向持仓模式：一个交易对只能存在一个方向的持仓</p>
          <p>双向持仓模式：一个交易对可以同时存在多空双向持仓</p>
          <p class="text-warning">注意：切换持仓模式前请确保没有持仓和挂单</p>
        </el-alert>
        
        <el-form
          ref="positionModeFormRef"
          :model="positionModeForm"
          label-width="120px"
          label-position="right"
          class="mt-4"
        >
          <el-form-item label="持仓模式" prop="dualSidePosition">
            <el-radio-group v-model="positionModeForm.dualSidePosition">
              <el-radio :label="false">单向持仓</el-radio>
              <el-radio :label="true">双向持仓</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="positionModeVisible = false">取消</el-button>
          <el-button type="primary" @click="submitPositionModeChange" :loading="positionModeLoading">
            确认设置
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <grid-trade-dialog
      v-model="showGridTradeDialog"
      :account="currentAccount"
      :selectedAccounts="isBatchMode ? selectedAccounts : []"
      @success="handleGridTradeSuccess"
    />
    
    <margin-account-dialog
      v-model="marginAccountVisible"
      :account="currentAccount"
    />
    
    <!-- 批量设置杠杆对话框 -->
    <el-dialog
      v-model="leverageDialogVisible"
      title="批量设置杠杆倍数"
      width="500px"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      >
        <p>将为选中的 {{ selectedAccounts.length }} 个子账号设置杠杆倍数</p>
        <p>交易对: {{ globalSymbol }}</p>
        <p>合约类型: {{ contractType === 'UM' ? 'U本位合约' : '币本位合约' }}</p>
      </el-alert>
      
      <el-form
        ref="leverageFormRef"
        :model="leverageForm"
        label-width="120px"
        label-position="right"
        class="mt-4"
      >
        <el-form-item label="杠杆倍数" prop="leverage">
          <el-slider
            v-model="leverageForm.leverage"
            :min="1"
            :max="125"
            :step="1"
            :marks="{1: '1x', 20: '20x', 50: '50x', 75: '75x', 100: '100x', 125: '125x'}"
            show-input
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="leverageDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitBatchLeverage" :loading="leverageLoading">
            确认设置
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 批量设置还款模式对话框 -->
    <el-dialog
      v-model="repayModeDialogVisible"
      title="批量设置还款模式"
      width="500px"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      >
        <p>将为选中的 {{ selectedAccounts.length }} 个子账号设置还款模式</p>
        <p>自动还款: 系统会自动使用可用余额偿还负余额</p>
        <p>手动还款: 需要手动操作进行负余额偿还</p>
      </el-alert>
      
      <el-form
        ref="repayModeFormRef"
        :model="repayModeForm"
        label-width="120px"
        label-position="right"
        class="mt-4"
      >
        <el-form-item label="还款模式" prop="autoRepay">
          <el-radio-group v-model="repayModeForm.autoRepay">
            <el-radio :label="false">手动还款</el-radio>
            <el-radio :label="true">自动还款</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="repayModeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitBatchRepayMode" :loading="repayModeLoading">
            确认设置
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 批量查询还款模式对话框 -->
    <el-dialog
      v-model="getRepayModeDialogVisible"
      title="批量查询还款模式"
      width="600px"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      >
        <p>查询选中的 {{ selectedAccounts.length }} 个子账号的还款模式</p>
      </el-alert>
      
      <el-table
        :data="repayModeQueryResults"
        style="width: 100%"
        max-height="400px"
        v-loading="getRepayModeLoading"
      >
        <el-table-column prop="email" label="子账号邮箱" min-width="180" />
        <el-table-column prop="autoRepay" label="还款模式" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.autoRepay ? 'success' : 'warning'">
              {{ scope.row.autoRepay ? '自动还款' : '手动还款' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="查询状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'">
              {{ scope.row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error" label="错误信息" />
      </el-table>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="getRepayModeDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="refreshRepayModeQuery" :loading="getRepayModeLoading">
            刷新查询
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 批量执行还款对话框 -->
    <el-dialog
      v-model="futuresRepayDialogVisible"
      title="批量执行还款"
      width="600px"
    >
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        class="mb-4"
      >
        <p>将为选中的 {{ selectedAccounts.length }} 个子账号执行负余额还款操作</p>
        <p>请确保选择正确的币种和还款金额</p>
      </el-alert>
      
      <el-form
        ref="futuresRepayFormRef"
        :model="futuresRepayForm"
        label-width="120px"
        label-position="right"
        class="mt-4"
        :rules="futuresRepayRules"
      >
        <el-form-item label="还款币种" prop="coin">
          <el-select v-model="futuresRepayForm.coin" placeholder="请选择币种" style="width: 100%">
            <el-option label="USDT" value="USDT" />
            <el-option label="BUSD" value="BUSD" />
            <el-option label="BNB" value="BNB" />
            <el-option label="BTC" value="BTC" />
            <el-option label="ETH" value="ETH" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="还款金额" prop="amount">
          <el-input-number 
            v-model="futuresRepayForm.amount" 
            :precision="8"
            :step="0.1"
            :min="0"
            style="width: 100%"
            placeholder="请输入还款金额"
          ></el-input-number>
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="futuresRepayForm.allDebt">全额还款（如选择则金额无效）</el-checkbox>
        </el-form-item>
      </el-form>
      
      <div class="repay-results-container" v-if="futuresRepayResults.length > 0">
        <h3>还款结果</h3>
        <el-table
          :data="futuresRepayResults"
          style="width: 100%"
          max-height="200px"
        >
          <el-table-column prop="email" label="子账号邮箱" min-width="180" />
          <el-table-column prop="status" label="还款状态" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'">
                {{ scope.row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="详细信息" />
        </el-table>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="futuresRepayDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="submitBatchFuturesRepay" :loading="futuresRepayLoading">
            执行还款
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue';
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus';
import axios from 'axios';
import { getCurrentUser } from '../services/auth';
import PositionList from '@/components/PositionList.vue';
import AutoArbitrageDialog from '@/components/dialogs/AutoArbitrageDialog.vue';
import LimitOrderList from '@/components/LimitOrderList.vue';
import TradeHistoryList from '@/components/TradeHistoryList.vue';
import MarginTradeHistory from '@/components/MarginTradeHistory.vue';
import TradeFeesSummary from '../components/TradeFeesSummary.vue'
import { getCacheStatus, clearCache } from '../services/tradesCache'
import { getOrdersData } from '../services/ordersCache'
import GridTradeDialog from '@/components/dialogs/GridTradeDialog.vue';
import MarginAccountDialog from '@/components/dialogs/MarginAccountDialog.vue';
import { useMarginTradesStore } from '../stores/marginTradesStore'

export default {
  name: 'TradingCenter',
  components: {
    PositionList,
    LimitOrderList,
    AutoArbitrageDialog,
    GridTradeDialog,
    TradeHistoryList,
    MarginTradeHistory,
    TradeFeesSummary,
    MarginAccountDialog
  },
  setup() {
    // 查询起始时间，默认为当前登录时间
    // 从本地存储中获取，如果没有就使用当前时间
    const savedStartTime = localStorage.getItem('queryStartTime');
    const queryStartTime = ref(savedStartTime ? parseInt(savedStartTime) : Date.now());
    
    // 全局交易对设置
    const savedGlobalSymbol = localStorage.getItem('globalSymbol');
    const globalSymbol = ref(savedGlobalSymbol || '');
    
    // 添加全局合约类型设置
    const savedContractType = localStorage.getItem('contractType');
    const contractType = ref(savedContractType || 'UM'); // 默认为U本位合约
    
    // 添加组件引用
    const positionListRef = ref(null);
    const limitOrderListRef = ref(null);
    const tradeHistoryListRef = ref(null);
    
    // 交易对列表
    const tradingPairs = ref([]);
    
    // 子账号数据
    const subaccounts = ref([]);
    const selectedAccounts = ref([]);
    const searchKeyword = ref('');
    const loading = ref(false);
    const subaccountTable = ref(null);
    
    // 持仓数据
    const positions = ref([]);
    const orders = ref([]);
    
    // 添加持仓版本变量，用于跟踪持仓变化
    const positionVersion = ref(0);
    
    // 对话框控制
    const showAutoArbitrageDialog = ref(false);
    const marginAccountVisible = ref(false);
    const showGridTradeDialog = ref(false);
    const currentAccount = ref(null);
    const isBatchMode = ref(false);
    
    // 系统消息窗口
    const showMessageWindow = ref(false);
    const systemMessages = ref([]);
    
    // 过滤子账号列表
    const filteredSubaccounts = computed(() => {
      if (!searchKeyword.value) {
        return subaccounts.value;
      }
      
      return subaccounts.value.filter(account => 
        account.email.toLowerCase().includes(searchKeyword.value.toLowerCase())
      );
    });
    
    // 加载子账号列表
    const loadSubaccounts = async () => {
      loading.value = true;
      
      try {
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          loading.value = false;
          return;
        }
        
        const response = await axios.get('/api/subaccounts', {
          params: {
            user_id: user.id
          },
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        });
        
        if (response.data.success) {
          // 处理返回的数据，添加API状态字段
          const accountsData = response.data.data.map(account => ({
            ...account,
            has_api_key: !!account.api_key // 将API密钥存在性转换为布尔值
          }));
          
          // 先检查之前选中的账号，保持选择状态
          const previousSelected = new Set(selectedAccounts.value.map(acc => acc.email));
          
          // 更新子账号列表
          subaccounts.value = accountsData;
          
          // 在下一个渲染周期后恢复选择状态
          setTimeout(() => {
            if (subaccountTable.value) {
              accountsData.forEach(account => {
                if (previousSelected.has(account.email)) {
                  subaccountTable.value.toggleRowSelection(account, true);
                }
              });
            }
          }, 100);
          
          ElMessage.success('加载子账号列表成功');
        } else {
          ElMessage.error(response.data.message || '加载子账号列表失败');
        }
      } catch (error) {
        console.error('加载子账号失败:', error);
        ElMessage.error('网络错误，加载子账号列表失败');
      } finally {
        loading.value = false;
      }
    };
    
    // 检查子账号是否可选
    const checkSelectable = (row) => {
      return row.has_api_key;
    };
    
    // 处理表格选择变化
    const handleSelectionChange = (val) => {
      // 确保只有有API key的子账号能被选中
      selectedAccounts.value = val.filter(account => account.has_api_key);
    };
    
    // 全选
    const selectAll = () => {
      // 只选择有API key的子账号
      filteredSubaccounts.value
        .filter(account => account.has_api_key)
        .forEach(row => {
          subaccountTable.value.toggleRowSelection(row, true);
        });
    };
    
    // 取消全选
    const deselectAll = () => {
      subaccountTable.value.clearSelection();
    };
    
    // 刷新子账号列表
    const refreshSubaccounts = () => {
      loadSubaccounts();
    };
    
    // 查看账户详情
    const viewAccountDetails = (account) => {
      if (!account || !account.has_api_key) {
        ElMessage.warning('账号未配置API密钥，无法查看详情');
        return;
      }
      
      // 确保复制账户对象，避免引用问题
      currentAccount.value = { ...account };
      marginAccountVisible.value = true;
    };
    
    // 打开自动套利对话框
    const openAutoArbitrage = (account) => {
      currentAccount.value = account;
      isBatchMode.value = false;
      showAutoArbitrageDialog.value = true;
    };
    
    // 打开网格交易对话框
    const openGridTrading = (account) => {
      currentAccount.value = account;
      isBatchMode.value = false;
      showGridTradeDialog.value = true;
    };
    
    // 批量自动套利
    const batchAutoArbitrage = () => {
      // 检查是否有选择账号
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      // 检查是否所有选中账号都有API密钥
      const allHaveApiKey = selectedAccounts.value.every(account => account.has_api_key);
      if (!allHaveApiKey) {
        ElMessage.warning('部分选中账号未配置API密钥，无法进行操作');
        return;
      }
      
      currentAccount.value = null;
      isBatchMode.value = true;
      showAutoArbitrageDialog.value = true;
    };
    
    // 批量网格建仓
    const batchGridTrading = () => {
      // 检查是否有选择账号
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      // 检查是否所有选中账号都有API密钥
      const allHaveApiKey = selectedAccounts.value.every(account => account.has_api_key);
      if (!allHaveApiKey) {
        ElMessage.warning('部分选中账号未配置API密钥，无法进行操作');
        return;
      }
      
      currentAccount.value = null;
      isBatchMode.value = true;
      showGridTradeDialog.value = true;
    };
    
    // 显示杠杆账户详情对话框
    const batchMarginDetails = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      marginAccountVisible.value = true;
    };
      
    // 批量设置持仓模式
    const batchPositionModeSettings = async () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      // 批量设置多个子账号时，显示确认对话框
      if (selectedAccounts.value.length > 1) {
        try {
          await ElMessageBox.confirm(
            `您选择了 ${selectedAccounts.value.length} 个子账号，确认要对它们统一设置持仓模式吗？`,
            '批量设置持仓模式确认',
            {
              confirmButtonText: '确认',
              cancelButtonText: '取消',
              type: 'warning'
            }
          );
        } catch (error) {
          return; // 用户取消操作
        }
      }
      
      // 批量模式下创建一个虚拟的当前账号，包含所有选中的子账号
      currentAccount.value = { 
        email: selectedAccounts.value.map(acc => acc.email).join(', '),
        isBatchMode: true 
      };
      
      positionModeForm.value.dualSidePosition = false; // 默认单向持仓
      positionModeVisible.value = true;
    };
    
    // 重新编写持仓模式设置提交函数，支持批量模式
    const submitPositionModeChange = async () => {
      if (!currentAccount.value) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      try {
        positionModeLoading.value = true;
        
        const isBatchMode = currentAccount.value.isBatchMode;
        let confirmMessage = isBatchMode 
          ? `确认要为 ${selectedAccounts.value.length} 个子账号设置${positionModeForm.value.dualSidePosition ? '双向' : '单向'}持仓模式吗？`
          : `确认要为 ${currentAccount.value.email} 设置${positionModeForm.value.dualSidePosition ? '双向' : '单向'}持仓模式吗？`;
        
        await ElMessageBox.confirm(
          confirmMessage,
          '持仓模式设置确认',
          {
            confirmButtonText: '确认设置',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          return;
        }
        
        // 批量模式下遍历所有选中的子账号
        if (isBatchMode) {
          const successAccounts = [];
          const failedAccounts = [];
          
          // 创建加载提示
          const loadingInstance = ElLoading.service({
            lock: true,
            text: `正在批量设置持仓模式 (0/${selectedAccounts.value.length})`,
            background: 'rgba(0, 0, 0, 0.7)'
          });
          
          // 顺序处理每个账号以避免API限流
          for (let i = 0; i < selectedAccounts.value.length; i++) {
            const account = selectedAccounts.value[i];
            
            // 更新加载提示
            loadingInstance.setText(`正在批量设置持仓模式 (${i}/${selectedAccounts.value.length})`);
            
            try {
              const response = await axios.post('/api/subaccounts/futures-positions/dual-side', {
                email: account.email,
                dualSidePosition: positionModeForm.value.dualSidePosition
              }, {
                headers: {
                  'Authorization': `Bearer ${user.token}`
                }
              });
              
              if (response.data.success) {
                successAccounts.push(account.email);
              } else {
                failedAccounts.push({
                  email: account.email,
                  error: response.data.error || '未知错误'
                });
              }
              
              // 添加小延迟避免API限流
              if (i < selectedAccounts.value.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 300));
              }
            } catch (error) {
              failedAccounts.push({
                email: account.email,
                error: error.message || '请求失败'
              });
            }
          }
          
          // 关闭加载提示
          loadingInstance.close();
          
          // 显示结果
          if (successAccounts.length > 0) {
            ElMessage.success(`成功为 ${successAccounts.length} 个子账号设置${positionModeForm.value.dualSidePosition ? '双向' : '单向'}持仓模式`);
          }
          
          if (failedAccounts.length > 0) {
            ElMessage.warning(`${failedAccounts.length} 个子账号设置失败`);
            console.error('持仓模式设置失败的账号:', failedAccounts);
          }
          
          positionModeVisible.value = false;
        } else {
          // 单账号模式
          const response = await axios.post('/api/subaccounts/futures-positions/dual-side', {
            email: currentAccount.value.email,
            dualSidePosition: positionModeForm.value.dualSidePosition
          }, {
            headers: {
              'Authorization': `Bearer ${user.token}`
            }
          });
          
          if (response.data.success) {
            ElMessage.success(`已成功设置${positionModeForm.value.dualSidePosition ? '双向' : '单向'}持仓模式`);
            positionModeVisible.value = false;
          } else {
            ElMessage.error(response.data.error || '设置持仓模式失败');
          }
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('设置持仓模式失败:', error);
          ElMessage.error('设置持仓模式失败');
        }
      } finally {
        positionModeLoading.value = false;
      }
    };
    
    // 加载交易对列表
    const loadTradingPairs = async () => {
      try {
        const response = await axios.get('/api/trading-pairs/', {
          params: {
            favorite: 'true' // 只获取收藏的交易对
          }
        });
        
        if (response.data.success && response.data.data && response.data.data.length > 0) {
          // 根据当前合约类型格式化交易对列表
          tradingPairs.value = response.data.data.map(pair => {
            // 根据当前合约类型调整显示和值
            let symbol = pair.symbol;
            let description = pair.description;
            
            if (contractType.value === 'CM' && symbol.endsWith('USDT')) {
              // 如果是币本位合约，将USDT格式转换为USD_PERP格式
              symbol = symbol.replace('USDT', 'USD_PERP');
              description = description.replace('USDT', 'USD永续');
            } else if (contractType.value === 'UM' && symbol.endsWith('USD_PERP')) {
              // 如果是U本位合约，将USD_PERP格式转换为USDT格式
              symbol = symbol.replace('USD_PERP', 'USDT');
              description = description.replace('USD永续', 'USDT');
            }
            
            return {
              label: `${symbol} - ${description}`,
              value: symbol
            };
          });
          
          // 如果没有设置全局交易对但有收藏的交易对，自动设置第一个为全局交易对
          if (!globalSymbol.value && tradingPairs.value.length > 0) {
            globalSymbol.value = tradingPairs.value[0].value;
            localStorage.setItem('globalSymbol', globalSymbol.value);
            ElMessage.success(`已自动设置全局交易对: ${globalSymbol.value}`);
          }
        } else {
          console.error('获取交易对失败或无收藏交易对');
          // 使用默认交易对列表作为备用
          tradingPairs.value = [
            { 
              label: contractType.value === 'CM' ? 'BTCUSD_PERP - 比特币/USD永续' : 'BTCUSDT - 比特币/USDT', 
              value: contractType.value === 'CM' ? 'BTCUSD_PERP' : 'BTCUSDT' 
            },
            { 
              label: contractType.value === 'CM' ? 'ETHUSD_PERP - 以太坊/USD永续' : 'ETHUSDT - 以太坊/USDT', 
              value: contractType.value === 'CM' ? 'ETHUSD_PERP' : 'ETHUSDT' 
            }
          ];
          
          // 如果没有设置全局交易对，自动设置第一个为全局交易对
          if (!globalSymbol.value) {
            globalSymbol.value = tradingPairs.value[0].value;
            localStorage.setItem('globalSymbol', globalSymbol.value);
          }
        }
      } catch (error) {
        console.error('获取交易对失败:', error);
        // 使用默认交易对列表作为备用
        tradingPairs.value = [
          { 
            label: contractType.value === 'CM' ? 'BTCUSD_PERP - 比特币/USD永续' : 'BTCUSDT - 比特币/USDT', 
            value: contractType.value === 'CM' ? 'BTCUSD_PERP' : 'BTCUSDT' 
          },
          { 
            label: contractType.value === 'CM' ? 'ETHUSD_PERP - 以太坊/USD永续' : 'ETHUSDT - 以太坊/USDT', 
            value: contractType.value === 'CM' ? 'ETHUSD_PERP' : 'ETHUSDT' 
          }
        ];
        
        // 如果没有设置全局交易对，自动设置第一个为全局交易对
        if (!globalSymbol.value) {
          globalSymbol.value = tradingPairs.value[0].value;
          localStorage.setItem('globalSymbol', globalSymbol.value);
        }
      }
    };
    
    // 创建通用的更新杠杆历史数据函数
    const updateMarginTradesData = (operationType) => {
      if (activeTab.value !== 'margin') {
        // 使用延时确保API请求不会太频繁
        setTimeout(async () => {
          try {
            // 直接使用MarginTradesStore来获取杠杆历史数据并缓存
            const marginTradesStore = useMarginTradesStore();
            
            // 构建请求参数
            const storeParams = {
              emails: selectedAccounts.value.map(account => account.email),
              symbol: globalSymbol.value || '',
              limit: 50,
              startTime: queryStartTime.value || undefined,
              useCache: false // 强制刷新，获取最新数据
            };
            
            // 通过Store获取数据
            await marginTradesStore.fetchMarginTrades(storeParams);
            
            console.log(`${operationType}后已更新杠杆历史数据，缓存记录数:`, marginTradesStore.marginTrades.length);
            
            // 添加系统消息通知
            addSystemMessage('info', '杠杆历史数据已更新', `${operationType}后已刷新杠杆历史数据，以确保手续费计算正常`);
          } catch (error) {
            console.error(`${operationType}后更新杠杆历史数据失败:`, error);
          }
        }, 1000); // 延迟1秒执行，避免API请求过于频繁
      }
    };
    
    // 处理套利成功
    const handleArbitrageSuccess = (result) => {
      ElMessage.success(`套利操作完成，成功: ${result.success}`);
      
      // 套利操作完成后，主动请求一次杠杆历史，并缓存到前端，以保证手续费计算正常
      updateMarginTradesData('套利操作');
    };
    
    // 处理网格交易成功
    const handleGridTradeSuccess = (result) => {
      ElMessage.success(`网格建仓操作完成，成功: ${result.success ? '是' : '否'}`);
      
      // 网格交易完成后，也需要主动请求一次杠杆历史，并缓存到前端，以保证手续费计算正常
      updateMarginTradesData('网格交易');
    };
    
    // 处理批量平仓对话框
    const openBatchCloseDialog = (data) => {
      console.log('批量平仓请求已接收:', data);
      // 暂不实现具体平仓逻辑，避免用户误操作
      ElMessage.info('批量平仓功能暂未启用');
    };
    
    // 监听对话框关闭，清理当前账号对象
    watch(marginAccountVisible, (val) => {
      if (!val) {
        // 对话框关闭时，延迟清理currentAccount防止卸载错误
        setTimeout(() => {
          if (!showAutoArbitrageDialog.value && !showGridTradeDialog.value) {
            currentAccount.value = null;
          }
        }, 100);
      }
    });
    
    watch(showAutoArbitrageDialog, (val) => {
      if (!val) {
        // 对话框关闭时，延迟清理currentAccount防止卸载错误
        setTimeout(() => {
          if (!marginAccountVisible.value && !showGridTradeDialog.value) {
            currentAccount.value = null;
            isBatchMode.value = false;
          }
        }, 100);
      }
    });
    
    watch(showGridTradeDialog, (val) => {
      if (!val) {
        // 对话框关闭时，延迟清理currentAccount防止卸载错误
        setTimeout(() => {
          if (!marginAccountVisible.value && !showAutoArbitrageDialog.value) {
          currentAccount.value = null;
            isBatchMode.value = false;
          }
        }, 100);
      }
    });
    
    // 加载持仓数据
    const loadPositions = async () => {
      if (selectedAccounts.value.length === 0) {
        return;
      }

      try {
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          return;
        }
        
        // 构建请求参数
        const emails = selectedAccounts.value.map(account => account.email);
        
        const response = await axios.post('/api/subaccounts/futures-positions', {
          emails: emails,
          user_id: user.id  // 添加用户ID
        }, {
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        });
        
        if (response.data.success) {
          positions.value = response.data.data || [];
          
          // 递增持仓版本，通知其他组件持仓已变化
          positionVersion.value++;
          console.log(`持仓数据已更新，当前版本: ${positionVersion.value}`);
          
          ElMessage.success(`成功加载${positions.value.length}个持仓信息`);
        } else {
          ElMessage.warning(response.data.error || '加载持仓信息失败');
        }
      } catch (error) {
        console.error('加载持仓信息失败:', error);
        ElMessage.error('网络错误，加载持仓信息失败');
      }
    };
    
    // 加载订单数据
    const loadOrders = async () => {
      if (selectedAccounts.value.length === 0) {
        return;
      }

      try {
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          return;
        }
        
        // 构建请求参数
        const emails = selectedAccounts.value.map(account => account.email);
        
        // 使用缓存服务获取订单数据
        const params = {
          emails: emails,
          user_id: user.id,
          contractType: contractType.value
        };
        
        // 使用缓存服务获取数据，强制刷新
        const result = await getOrdersData(params, true, 3000);
        
        if (result.success) {
          orders.value = result.data || [];
          ElMessage.success(`成功加载${orders.value.length}个${contractType.value === 'UM' ? 'U本位' : '币本位'}合约订单信息`);
        } else {
          ElMessage.warning(result.error || `加载${contractType.value === 'UM' ? 'U本位' : '币本位'}合约订单信息失败`);
        }
      } catch (error) {
        console.error(`加载${contractType.value === 'UM' ? 'U本位' : '币本位'}合约订单信息失败:`, error);
        ElMessage.error(`网络错误，加载${contractType.value === 'UM' ? 'U本位' : '币本位'}合约订单信息失败`);
      }
    };
    
    // 重置查询时间为登录时间
    const resetQueryStartTime = () => {
      queryStartTime.value = Date.now();
      localStorage.setItem('queryStartTime', queryStartTime.value.toString());
      ElMessage.success('已重置为当前时间');
    };
    
    // 处理全局交易对变化
    const handleGlobalSymbolChange = (val) => {
      globalSymbol.value = val;
      localStorage.setItem('globalSymbol', val || '');
      
      // 如果设置了新的全局交易对，通知用户
      if (val) {
        ElMessage.success(`已设置全局交易对: ${val}`);
      } else {
        ElMessage.info('已清除全局交易对设置');
      }
    };
    
    // 添加处理合约类型变化函数
    const handleContractTypeChange = (val) => {
      contractType.value = val;
      localStorage.setItem('contractType', val);
      ElMessage.success(`已切换为${val === 'UM' ? 'U本位' : '币本位'}合约`);
      
      // 重新加载交易对列表
      loadTradingPairs();
      
      // 如果有全局交易对，尝试转换格式
      if (globalSymbol.value) {
        if (val === 'CM' && globalSymbol.value.endsWith('USDT')) {
          // 从U本位转为币本位
          const newGlobalSymbol = globalSymbol.value.replace('USDT', 'USD_PERP');
          globalSymbol.value = newGlobalSymbol;
          localStorage.setItem('globalSymbol', newGlobalSymbol);
          ElMessage.info(`全局交易对已调整为: ${newGlobalSymbol}`);
        } else if (val === 'UM' && globalSymbol.value.endsWith('USD_PERP')) {
          // 从币本位转为U本位
          const newGlobalSymbol = globalSymbol.value.replace('USD_PERP', 'USDT');
          globalSymbol.value = newGlobalSymbol;
          localStorage.setItem('globalSymbol', newGlobalSymbol);
          ElMessage.info(`全局交易对已调整为: ${newGlobalSymbol}`);
        }
      }
    };
    
    // 监听查询时间变化，保存到本地存储
    watch(() => queryStartTime.value, (newVal) => {
      localStorage.setItem('queryStartTime', newVal.toString());
    });
    
    // 新增的activeTab状态
    const activeTab = ref('trades');
    
    // 组件运行状态控制
    const showComponentStatus = ref(false);
    const componentStatusList = ref([
      { component: 'PositionList', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' },
      { component: 'LimitOrderList', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' },
      { component: 'TradeHistoryList', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' },
      { component: 'MarginTradeHistory', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' },
      { component: 'TradeFeesSummary', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' },
      { component: 'AutoArbitrageDialog', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' },
      { component: 'GridTradeDialog', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' },
      { component: 'MarginAccountDialog', status: '正常', lastUpdate: new Date().toLocaleString(), message: '组件正常运行中' }
    ]);

    // 更新组件状态的方法
    const updateComponentStatus = (componentName, status, message) => {
      const index = componentStatusList.value.findIndex(item => item.component === componentName);
      if (index !== -1) {
        componentStatusList.value[index].status = status;
        componentStatusList.value[index].message = message;
        componentStatusList.value[index].lastUpdate = new Date().toLocaleString();
      } else {
        componentStatusList.value.push({
          component: componentName,
          status: status,
          lastUpdate: new Date().toLocaleString(),
          message: message
        });
      }
    };
    
    // 扩展handleChildMessage方法，处理组件状态更新
    const handleChildMessage = (message) => {
      // 只有当消息类型是警告(warning)或错误(error)时才添加到系统消息
      if (message && (message.type === 'warning' || message.type === 'error') && message.title) {
        addSystemMessage(message.type, message.title, message.description || '');
      }
      
      // 更新组件状态（无论正常还是异常，都更新状态列表）
      if (message.componentStatus) {
        updateComponentStatus(
          message.componentStatus.component,
          message.componentStatus.status,
          message.componentStatus.message
        );
        
        // 对于异常状态，特别设置状态图标为可见
        if (message.componentStatus.status !== '正常') {
          showComponentStatus.value = true;
        }
      }
    };
    
    // 计算异常状态组件数量
    const abnormalComponentCount = computed(() => {
      return componentStatusList.value.filter(item => item.status !== '正常').length;
    });
    
    // 添加缓存管理相关函数
    const cacheStatus = ref(getCacheStatus());
    const showCacheInfo = ref(false);
    
    // 更新缓存状态信息
    const updateCacheStatus = () => {
      cacheStatus.value = getCacheStatus();
    };
    
    // 清除缓存数据
    const handleClearCache = () => {
      clearCache();
      updateCacheStatus();
      ElMessage.success('交易数据缓存已清除');
    };
    
    // 定期更新缓存状态
    const cacheStatusTimer = ref(null);
    const startCacheStatusTimer = () => {
      stopCacheStatusTimer();
      cacheStatusTimer.value = setInterval(() => {
        updateCacheStatus();
      }, 5000); // 每5秒更新一次
    };
    
    const stopCacheStatusTimer = () => {
      if (cacheStatusTimer.value) {
        clearInterval(cacheStatusTimer.value);
        cacheStatusTimer.value = null;
      }
    };
    
    // 添加系统消息
    const addSystemMessage = (type, title, description) => {
      systemMessages.value.push({
        type, // success, warning, info, error
        title,
        description,
        time: new Date().toLocaleTimeString()
      });
      
      // 显示消息窗口
      showMessageWindow.value = true;
    };
    
    // 清空所有消息
    const clearMessages = () => {
      systemMessages.value = [];
    };
    
    // 刷新所有数据
    const refreshAllData = (showMessage = true) => {
      // 仅当手动刷新时才刷新子账号数据
      if (showMessage) {
        refreshSubaccounts();
      }
      
      // 刷新订单数据
      loadOrders();
      
      // 刷新持仓数据
      loadPositions();
      
      // 手动刷新持仓管理组件
      if (positionListRef.value) {
        positionListRef.value.fetchPositions();
      }
      
      if (showMessage) {
        ElMessage.success('已手动刷新所有数据');
      }
    };
    
    // 组件挂载时执行
    onMounted(() => {
      startCacheStatusTimer();
      loadSubaccounts();
      loadPositions();
      loadOrders();
      loadTradingPairs();
    });
    
    // 组件卸载时清理资源
    onUnmounted(() => {
      stopCacheStatusTimer();
    });
    
    // 持仓模式设置相关变量和函数
    const positionModeVisible = ref(false);
    const positionModeFormRef = ref(null);
    const positionModeForm = ref({
      dualSidePosition: false // 默认单向持仓
    });
    const positionModeLoading = ref(false);
    
    // 打开持仓模式设置对话框
    const openPositionModeSettings = (account) => {
      currentAccount.value = account;
      positionModeForm.value.dualSidePosition = false; // 默认单向持仓
      positionModeVisible.value = true;
    };
    
    // 添加全局刷新间隔变量
    const globalRefreshInterval = ref(parseInt(localStorage.getItem('globalRefreshInterval')) || 30);
    const globalRefreshTimer = ref(null);
    
    // 处理刷新间隔变化
    const handleRefreshIntervalChange = (val) => {
      localStorage.setItem('globalRefreshInterval', val.toString());
      ElMessage.success(`已更新刷新间隔为${val}秒`);
    };
    
    // 启动全局自动刷新定时器 - 保留函数但不再自动调用
    // eslint-disable-next-line no-unused-vars
    const startGlobalRefreshTimer = () => {
      stopGlobalRefreshTimer();
      globalRefreshTimer.value = setInterval(() => {
        // 刷新所有数据，但不显示消息提示以避免干扰
        refreshAllData(false);
        console.log(`自动刷新已执行，间隔: ${globalRefreshInterval.value}秒，时间:`, new Date().toLocaleTimeString());
      }, globalRefreshInterval.value * 1000); // 使用用户设置的间隔时间（秒转毫秒）
    };
    
    // 停止全局自动刷新定时器
    const stopGlobalRefreshTimer = () => {
      if (globalRefreshTimer.value) {
        clearInterval(globalRefreshTimer.value);
        globalRefreshTimer.value = null;
      }
    };
    
    // 批量设置杠杆对话框
    const leverageDialogVisible = ref(false);
    const leverageForm = ref({
      leverage: 20 // 默认20倍杠杆
    });
    const leverageLoading = ref(false);
    const leverageFormRef = ref(null);
    
    // 打开批量设置杠杆对话框
    const batchSetLeverage = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      if (!globalSymbol.value) {
        ElMessage.warning('请先设置全局交易对');
        return;
      }
      
      leverageForm.value.leverage = 20;  // 重置为默认值
      leverageDialogVisible.value = true;
    };
    
    // 提交批量杠杆设置
    const submitBatchLeverage = async () => {
      try {
        if (selectedAccounts.value.length === 0) {
          ElMessage.warning('请先选择子账号');
          return;
        }
        
        if (!globalSymbol.value) {
          ElMessage.warning('请先设置全局交易对');
        return;
      }
        
        const confirmMsg = `确认要为 ${selectedAccounts.value.length} 个子账号设置 ${globalSymbol.value} 的杠杆为 ${leverageForm.value.leverage}倍吗？`;
        
      try {
        await ElMessageBox.confirm(
            confirmMsg,
            '批量设置杠杆确认',
          {
              confirmButtonText: '确认',
            cancelButtonText: '取消',
              type: 'warning'
          }
        );
        } catch (e) {
          return; // 用户取消操作
        }
        
        leverageLoading.value = true;
        
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          leverageLoading.value = false;
          return;
        }
        
        // 构建API请求参数
        const params = {
          emails: selectedAccounts.value.map(acc => acc.email),
          symbol: globalSymbol.value,
          leverage: leverageForm.value.leverage,
          contractType: contractType.value
        };
        
        // 创建加载效果
        const loadingInstance = ElLoading.service({
          lock: true,
          text: `正在批量设置杠杆倍数 (0/${selectedAccounts.value.length})`,
          background: 'rgba(0, 0, 0, 0.7)'
        });
        
        // 发送批量设置杠杆请求
        const response = await axios.post('/api/subaccounts/portfolio-margin/um/batch-leverage', params, {
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        });
        
        // 关闭加载效果
        loadingInstance.close();
        
        if (response.data.success) {
          // 处理结果
          const results = response.data.data?.results || response.data.data || [];
          
          // 确保results是数组
          if (Array.isArray(results)) {
            const successCount = results.filter(r => r.success).length;
            const failCount = results.length - successCount;
            
            if (successCount === results.length) {
              ElMessage.success(`成功为 ${successCount} 个子账号设置杠杆倍数为 ${leverageForm.value.leverage}倍`);
      } else {
              ElMessage.warning(`部分设置成功: ${successCount}个成功, ${failCount}个失败`);
              console.log('详细结果:', results);
            }
          } else {
            // 如果results不是数组，显示成功消息
            ElMessage.success(`已成功提交杠杆设置请求，杠杆倍数: ${leverageForm.value.leverage}倍`);
            console.log('API返回数据:', response.data);
          }
          
          // 关闭对话框
          leverageDialogVisible.value = false;
        } else {
          ElMessage.error(response.data.error || '批量设置杠杆失败');
        }
      } catch (error) {
        console.error('批量设置杠杆异常:', error);
        ElMessage.error('批量设置杠杆异常: ' + (error.response?.data?.error || error.message || '未知错误'));
      } finally {
        leverageLoading.value = false;
      }
    };
    
    // 处理单个账户的资金归集
    const handleAutoCollection = async (account) => {
      try {
        await ElMessageBox.confirm(
          `确认要对子账号 ${account.email} 执行资金归集操作吗？此操作将把子账号的资金转移到主账号。`,
          '资金归集确认',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          return;
        }
        
        const loadingInstance = ElLoading.service({
          lock: true,
          text: '正在执行资金归集...',
          background: 'rgba(0, 0, 0, 0.7)'
        });
        
        try {
          const response = await axios.post('/api/portfolio/papi/v1/auto-collection', {
            email: account.email
          }, {
            headers: {
              'Authorization': `Bearer ${user.token}`
            },
            timeout: 30000 // 30秒超时
          });
          
          if (response.data.success) {
            ElMessage.success(`子账号 ${account.email} 资金归集成功`);
          } else {
            ElMessage.error(`子账号 ${account.email} 资金归集失败: ${response.data.error || '未知错误'}`);
          }
        } catch (error) {
          console.error('资金归集请求失败:', error);
          ElMessage.error(`资金归集请求失败: ${error.message || '未知错误'}`);
        } finally {
          loadingInstance.close();
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('处理资金归集操作失败:', error);
        }
      }
    };
    
    // 批量资金归集
    const batchAutoCollection = async () => {
      // 检查是否有选择账号
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      try {
        await ElMessageBox.confirm(
          `确认要为选中的 ${selectedAccounts.value.length} 个子账号执行资金归集操作吗？此操作将把子账号的资金转移到主账号。`,
          '批量资金归集确认',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          return;
        }
        
        // 创建加载提示
        const loadingInstance = ElLoading.service({
          lock: true,
          text: `正在批量执行资金归集 (0/${selectedAccounts.value.length})`,
          background: 'rgba(0, 0, 0, 0.7)'
        });
        
        // 记录成功和失败的账号
        const successAccounts = [];
        const failedAccounts = [];
        
        // 顺序处理每个账号，避免API限流
        for (let i = 0; i < selectedAccounts.value.length; i++) {
          const account = selectedAccounts.value[i];
          
          // 更新加载提示
          loadingInstance.setText(`正在批量执行资金归集 (${i+1}/${selectedAccounts.value.length})`);
          
          try {
            // 调用资金归集API
        const response = await axios.post('/api/portfolio/papi/v1/auto-collection', {
          email: account.email
        }, {
              headers: {
                'Authorization': `Bearer ${user.token}`
              },
              timeout: 30000 // 30秒超时
        });
            
        if (response.data.success) {
              successAccounts.push(account.email);
              addSystemMessage('success', `资金归集成功`, `子账号: ${account.email} 资金归集成功`);
        } else {
              failedAccounts.push({
                email: account.email,
                error: response.data.error || '未知错误'
              });
              addSystemMessage('error', `资金归集失败`, `子账号: ${account.email}, 错误: ${response.data.error || '未知错误'}`);
            }
            
            // 添加间隔，避免API限流
            if (i < selectedAccounts.value.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 1000));
            }
          } catch (error) {
            failedAccounts.push({
              email: account.email,
              error: error.message || '请求失败'
            });
            addSystemMessage('error', `资金归集请求异常`, `子账号: ${account.email}, 错误: ${error.message || '请求失败'}`);
            
            // 继续执行下一个账号的归集
            console.error(`子账号 ${account.email} 资金归集失败:`, error);
          }
        }
        
        // 关闭加载提示
        loadingInstance.close();
        
        // 显示结果
        if (successAccounts.length > 0) {
          ElMessage.success(`成功对 ${successAccounts.length} 个子账号执行资金归集`);
        }
        
        if (failedAccounts.length > 0) {
          ElMessage.warning(`${failedAccounts.length} 个子账号资金归集失败`);
          console.error('资金归集失败的账号:', failedAccounts);
        }
        
        // 显示消息窗口
        if (systemMessages.value.length > 0) {
          showMessageWindow.value = true;
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量资金归集操作失败:', error);
          ElMessage.error(`批量资金归集操作失败: ${error.message || '未知错误'}`);
        }
      }
    };
    
    // 批量设置还款模式相关变量
    const repayModeDialogVisible = ref(false);
    const repayModeForm = ref({
      autoRepay: false // 默认选择手动还款
    });
    const repayModeLoading = ref(false);
    const repayModeFormRef = ref(null);
    
    // 批量查询还款模式相关变量
    const getRepayModeDialogVisible = ref(false);
    const getRepayModeLoading = ref(false);
    const repayModeQueryResults = ref([]);
    
    // 批量设置还款模式对话框
    const batchSetRepayMode = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      repayModeForm.value.autoRepay = false; // 默认选择手动还款
      repayModeDialogVisible.value = true;
    };
    
    // 批量查询还款模式对话框
    const batchGetRepayMode = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      repayModeQueryResults.value = []; // 清空之前的查询结果
      getRepayModeDialogVisible.value = true;
      
      // 打开对话框后立即执行查询
      refreshRepayModeQuery();
    };
    
    // 刷新还款模式查询
    const refreshRepayModeQuery = async () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      getRepayModeLoading.value = true;
      
      const user = getCurrentUser();
      if (!user || !user.token) {
        ElMessage.error('用户未登录或token无效');
        getRepayModeLoading.value = false;
        return;
      }
      
      // 清空之前的查询结果
      repayModeQueryResults.value = [];
      
      // 顺序查询每个账号
      for (const account of selectedAccounts.value) {
        try {
          // 调用API查询还款模式
          const response = await axios.get('/api/portfolio/papi/v1/repay-futures-switch', {
            params: {
              email: account.email
            },
            headers: {
              'Authorization': `Bearer ${user.token}`
            },
            timeout: 15000 // 15秒超时
          });
          
          if (response.data.success) {
            repayModeQueryResults.value.push({
              email: account.email,
              autoRepay: response.data.data?.autoRepay || false,
              status: 'success',
              error: ''
            });
          } else {
            repayModeQueryResults.value.push({
              email: account.email,
              autoRepay: false,
              status: 'failed',
              error: response.data.error || '查询失败'
            });
          }
        } catch (error) {
          repayModeQueryResults.value.push({
            email: account.email,
            autoRepay: false,
            status: 'failed',
            error: error.message || '请求异常'
          });
          
          console.error(`子账号 ${account.email} 查询还款模式失败:`, error);
        }
        
        // 添加小延迟避免API限流
        if (selectedAccounts.value.length > 1) {
          await new Promise(resolve => setTimeout(resolve, 200));
        }
      }
      
      getRepayModeLoading.value = false;
    };
    
    // 提交批量设置还款模式
    const submitBatchRepayMode = async () => {
      try {
        if (selectedAccounts.value.length === 0) {
          ElMessage.warning('请先选择子账号');
          return;
        }
        
        const mode = repayModeForm.value.autoRepay ? '自动还款' : '手动还款';
        const confirmMsg = `确认要为 ${selectedAccounts.value.length} 个子账号设置${mode}模式吗？`;
        
        try {
          await ElMessageBox.confirm(
            confirmMsg,
            '批量设置还款模式确认',
            {
              confirmButtonText: '确认',
              cancelButtonText: '取消',
              type: 'warning'
            }
          );
        } catch (e) {
          return; // 用户取消操作
        }
        
        repayModeLoading.value = true;
        
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          repayModeLoading.value = false;
          return;
        }
        
        // 创建加载提示
        const loadingInstance = ElLoading.service({
          lock: true,
          text: `正在批量设置还款模式 (0/${selectedAccounts.value.length})`,
          background: 'rgba(0, 0, 0, 0.7)'
        });
        
        // 记录成功和失败的账号
        const successAccounts = [];
        const failedAccounts = [];
        
        // 顺序处理每个账号
        for (let i = 0; i < selectedAccounts.value.length; i++) {
          const account = selectedAccounts.value[i];
          
          // 更新加载提示
          loadingInstance.setText(`正在批量设置还款模式 (${i+1}/${selectedAccounts.value.length})`);
          
          try {
            // 调用API设置还款模式
            const response = await axios.post('/api/portfolio/papi/v1/repay-futures-switch', {
              email: account.email,
              autoRepay: repayModeForm.value.autoRepay
            }, {
              headers: {
                'Authorization': `Bearer ${user.token}`
              },
              timeout: 30000 // 30秒超时
            });
            
            if (response.data.success) {
              successAccounts.push(account.email);
              addSystemMessage('success', `设置${mode}成功`, `子账号: ${account.email}`);
            } else {
              failedAccounts.push({
                email: account.email,
                error: response.data.error || '未知错误'
              });
              addSystemMessage('error', `设置${mode}失败`, `子账号: ${account.email}, 错误: ${response.data.error || '未知错误'}`);
            }
            
            // 添加间隔，避免API限流
            if (i < selectedAccounts.value.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 500));
            }
          } catch (error) {
            failedAccounts.push({
              email: account.email,
              error: error.message || '请求失败'
            });
            addSystemMessage('error', `设置${mode}请求异常`, `子账号: ${account.email}, 错误: ${error.message || '请求失败'}`);
            
            console.error(`子账号 ${account.email} 设置${mode}失败:`, error);
          }
        }
        
        // 关闭加载提示
        loadingInstance.close();
        
        // 显示结果
        if (successAccounts.length > 0) {
          ElMessage.success(`成功对 ${successAccounts.length} 个子账号设置${mode}模式`);
        }
        
        if (failedAccounts.length > 0) {
          ElMessage.warning(`${failedAccounts.length} 个子账号设置${mode}失败`);
          console.error('设置还款模式失败的账号:', failedAccounts);
        }
        
        // 显示消息窗口
        if (systemMessages.value.length > 0) {
          showMessageWindow.value = true;
        }
        
        // 关闭对话框
        repayModeDialogVisible.value = false;
      } catch (error) {
        console.error('批量设置还款模式异常:', error);
        ElMessage.error('批量设置还款模式异常: ' + (error.response?.data?.error || error.message || '未知错误'));
      } finally {
        repayModeLoading.value = false;
      }
    };
    
    // 批量执行还款相关变量
    const futuresRepayDialogVisible = ref(false);
    const futuresRepayLoading = ref(false);
    const futuresRepayFormRef = ref(null);
    const futuresRepayForm = ref({
      coin: 'USDT',
      amount: 0,
      allDebt: true // 默认全额还款
    });
    const futuresRepayRules = {
      coin: [{ required: true, message: '请选择还款币种', trigger: 'change' }],
      amount: [{ required: true, message: '请输入还款金额', trigger: 'blur' }]
    };
    const futuresRepayResults = ref([]);
    
    // 打开批量还款对话框
    const batchFuturesRepay = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号');
        return;
      }
      
      // 重置表单数据
      futuresRepayForm.value = {
        coin: 'USDT',
        amount: 0,
        allDebt: true // 默认全额还款
      };
      futuresRepayResults.value = [];
      futuresRepayDialogVisible.value = true;
    };
    
    // 执行批量还款
    const submitBatchFuturesRepay = async () => {
      try {
        // 表单验证
        await futuresRepayFormRef.value.validate();
        
        if (selectedAccounts.value.length === 0) {
          ElMessage.warning('请先选择子账号');
          return;
        }
        
        if (!futuresRepayForm.value.allDebt && futuresRepayForm.value.amount <= 0) {
          ElMessage.warning('请输入有效的还款金额');
          return;
        }
        
        // 确认对话框
        const repayMode = futuresRepayForm.value.allDebt ? '全额还款' : `部分还款: ${futuresRepayForm.value.amount} ${futuresRepayForm.value.coin}`;
        await ElMessageBox.confirm(
          `确认要为 ${selectedAccounts.value.length} 个子账号执行${repayMode}操作吗？`,
          '批量还款确认',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        futuresRepayLoading.value = true;
        
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          futuresRepayLoading.value = false;
          return;
        }
        
        // 清空之前的结果
        futuresRepayResults.value = [];
        
        // 创建加载提示
        const loadingInstance = ElLoading.service({
          lock: true,
          text: `正在批量执行还款 (0/${selectedAccounts.value.length})`,
          background: 'rgba(0, 0, 0, 0.7)'
        });
        
        // 顺序处理每个账号
        for (let i = 0; i < selectedAccounts.value.length; i++) {
          const account = selectedAccounts.value[i];
          
          // 更新加载提示
          loadingInstance.setText(`正在批量执行还款 (${i+1}/${selectedAccounts.value.length})`);
          
          try {
            // 构建请求参数
            const params = {
              email: account.email,
              coin: futuresRepayForm.value.coin,
              allDebt: futuresRepayForm.value.allDebt
            };
            
            // 如果不是全额还款，添加金额参数
            if (!futuresRepayForm.value.allDebt) {
              params.amount = futuresRepayForm.value.amount;
            }
            
            // 调用API执行还款
            const response = await axios.post('/api/portfolio/papi/v1/futures-repay', params, {
              headers: {
                'Authorization': `Bearer ${user.token}`
              },
              timeout: 30000 // 30秒超时
            });
            
            if (response.data.success) {
              futuresRepayResults.value.push({
                email: account.email,
                status: 'success',
                message: response.data.message || '还款成功'
              });
              addSystemMessage('success', '还款成功', `子账号: ${account.email} 还款成功`);
            } else {
              futuresRepayResults.value.push({
                email: account.email,
                status: 'failed',
                message: response.data.error || '还款失败'
              });
              addSystemMessage('error', '还款失败', `子账号: ${account.email}, 错误: ${response.data.error || '未知错误'}`);
            }
          } catch (error) {
            futuresRepayResults.value.push({
              email: account.email,
              status: 'failed',
              message: error.message || '请求异常'
            });
            addSystemMessage('error', '还款请求异常', `子账号: ${account.email}, 错误: ${error.message || '请求失败'}`);
            
            console.error(`子账号 ${account.email} 执行还款失败:`, error);
          }
          
          // 添加小延迟避免API限流
          if (i < selectedAccounts.value.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 500));
          }
        }
        
        // 关闭加载提示
        loadingInstance.close();
        
        // 显示结果
        const successCount = futuresRepayResults.value.filter(result => result.status === 'success').length;
        const failCount = futuresRepayResults.value.length - successCount;
        
        if (successCount > 0) {
          ElMessage.success(`成功为 ${successCount} 个子账号执行还款操作`);
        }
        
        if (failCount > 0) {
          ElMessage.warning(`${failCount} 个子账号还款失败`);
        }
        
        // 显示消息窗口
        if (systemMessages.value.length > 0) {
          showMessageWindow.value = true;
        }
      } catch (error) {
        if (error === 'cancel') {
          return; // 用户取消操作
        }
        
        console.error('批量执行还款异常:', error);
        ElMessage.error('批量执行还款异常: ' + error.message || '未知错误');
      } finally {
        futuresRepayLoading.value = false;
      }
    };
    
    return {
      queryStartTime,
      resetQueryStartTime,
      globalSymbol,
      tradingPairs,
      handleGlobalSymbolChange,
      contractType,
      handleContractTypeChange,
      refreshAllData,
      positionListRef,
      limitOrderListRef,
      tradeHistoryListRef,
      subaccounts,
      selectedAccounts,
      searchKeyword,
      loading,
      subaccountTable,
      positions,
      orders,
      positionVersion,
      showAutoArbitrageDialog,
      marginAccountVisible,
      showGridTradeDialog,
      currentAccount,
      isBatchMode,
      filteredSubaccounts,
      loadSubaccounts,
      checkSelectable,
      handleSelectionChange,
      selectAll,
      deselectAll,
      refreshSubaccounts,
      viewAccountDetails,
      openAutoArbitrage,
      openGridTrading,
      batchAutoArbitrage,
      batchGridTrading,
      batchMarginDetails,
      handleArbitrageSuccess,
      handleGridTradeSuccess,
      loadPositions,
      loadOrders,
      activeTab,
      showMessageWindow,
      systemMessages,
      addSystemMessage,
      clearMessages,
      handleChildMessage,
      showComponentStatus,
      componentStatusList,
      abnormalComponentCount,
      cacheStatus,
      showCacheInfo,
      updateCacheStatus,
      handleClearCache,
      positionModeVisible,
      positionModeFormRef,
      positionModeForm,
      positionModeLoading,
      openPositionModeSettings,
      submitPositionModeChange,
      batchPositionModeSettings,
      globalRefreshInterval,
      handleRefreshIntervalChange,
      openBatchCloseDialog,
      leverageDialogVisible,
      leverageForm,
      leverageLoading,
      leverageFormRef,
      batchSetLeverage,
      submitBatchLeverage,
      handleAutoCollection,
      batchAutoCollection,
      repayModeDialogVisible,
      repayModeForm,
      repayModeLoading,
      repayModeFormRef,
      batchSetRepayMode,
      submitBatchRepayMode,
      // 新添加的属性
      getRepayModeDialogVisible,
      getRepayModeLoading,
      repayModeQueryResults,
      batchGetRepayMode,
      refreshRepayModeQuery,
      futuresRepayDialogVisible,
      futuresRepayLoading,
      futuresRepayFormRef,
      futuresRepayForm,
      futuresRepayRules,
      futuresRepayResults,
      batchFuturesRepay,
      submitBatchFuturesRepay,
    };
  }
};
</script>

<style scoped>
.trading-center-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.account-selection-card,
.batch-actions-card {
  margin-top: 20px;
}

.filter-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.filter-input {
  width: 200px;
}

.selection-actions {
  display: flex;
  gap: 10px;
}

.action-buttons {
  display: flex;
  gap: 5px;
}

.batch-buttons {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.batch-buttons .el-button {
  margin-bottom: 10px;
}

.mt-20 {
  margin-top: 20px;
}

.global-query-settings {
  border-radius: 4px;
  padding: 5px 10px;
  background-color: #f5f7fa;
  flex-wrap: wrap;
}

.setting-item {
  display: flex;
  align-items: center;
  margin: 5px 0;
}

.query-time-setting {
  border-radius: 4px;
  padding: 5px 10px;
  background-color: #f5f7fa;
}

.active-tab {
  font-weight: bold;
  box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.1);
  background-color: #409EFF !important;
  color: white !important;
}

.header-actions .el-button-group .el-button {
  min-width: 80px;
}

/* 消息窗口样式 */
.message-window-container {
  position: fixed;
  bottom: 80px;
  right: 10px;
  z-index: 1000;
  width: 400px;
  max-width: 90vw;
}

.message-window {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.message-window-header {
  background-color: #409EFF;
  color: white;
  padding: 10px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.message-window-controls {
  display: flex;
  gap: 5px;
}

.message-window-controls .el-button {
  color: white;
  padding: 0 5px;
}

.message-window-body {
  max-height: 300px;
  overflow-y: auto;
  padding: 10px;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.no-messages {
  text-align: center;
  color: #909399;
  padding: 20px 0;
}

/* 消息窗口悬浮按钮 */
.message-icon-container {
  position: fixed;
  bottom: 120px;
  right: 10px;
  z-index: 1000;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #409EFF;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.message-icon-container:hover {
  background-color: #3a8ee6;
}

.el-button.is-circle {
  padding: 0;
  width: 100%;
  height: 100%;
}

/* 组件运行状态悬浮框 */
.component-status-container {
  position: fixed;
  bottom: 80px;
  right: 10px;
  z-index: 1000;
  width: 400px;
  max-width: 90vw;
}

.component-status-window {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.component-status-header {
  background-color: #409EFF;
  color: white;
  padding: 10px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.component-status-controls {
  display: flex;
  gap: 5px;
}

.component-status-controls .el-button {
  color: white;
  padding: 0 5px;
}

.component-status-body {
  max-height: 300px;
  overflow-y: auto;
  padding: 10px;
}

.component-status-icon-container {
  position: fixed;
  bottom: 120px;
  right: 10px;
  z-index: 1000;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #409EFF;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.component-status-icon-container:hover {
  background-color: #3a8ee6;
}

/* 缓存状态窗口样式 */
.cache-status-container {
  position: fixed;
  bottom: 80px;
  right: 10px;
  z-index: 1000;
  width: 350px;
  max-width: 90vw;
}

.cache-status-window {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.cache-status-header {
  background-color: #67c23a;
  color: white;
  padding: 10px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cache-status-controls {
  display: flex;
  gap: 5px;
}

.cache-status-controls .el-button {
  color: white;
  padding: 0 5px;
}

.cache-status-body {
  padding: 15px;
}

.cache-info {
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.cache-description {
  font-size: 12px;
  color: #909399;
}

.cache-icon-container {
  position: fixed;
  bottom: 160px;
  right: 10px;
  z-index: 1000;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
</style>