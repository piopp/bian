import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { getCurrentUser } from '@/services/auth'

/**
 * u6760u6746u4ea4u6613u624bu7eedu8d39u76f8u5173u7684u5b58u50a8u5e93
 * u7528u4e8eu7ba1u7406u6760u6746u4ea4u6613u5386u53f2u548cu8ba1u7b97u624bu7eedu8d39
 */
export const useMarginTradesStore = defineStore('marginTrades', () => {
  // u72b6u6001
  const marginTrades = ref([])
  const isLoading = ref(false)
  const lastUpdateTime = ref(null)
  const errorMessage = ref('')
  const CACHE_DURATION = 5 * 60 * 1000 // 5u5206u949fu7f13u5b58

  // u8ba1u7b97u5c5eu6027
  const totalCommission = computed(() => {
    if (!marginTrades.value || marginTrades.value.length === 0) return 0;
    
    let total = 0;
    marginTrades.value.forEach(trade => {
      if (trade.commission) {
        // u6839u636eu624bu7eedu8d39u8d44u4ea7u7c7bu578bu8fdbu884cu5904u7406
        if (trade.commissionAsset === 'USDT') {
          // u76f4u63a5u7d2fu52a0 USDT u624bu7eedu8d39
          total += parseFloat(trade.commission || 0);
        } else if (trade.commissionAsset && trade.price) {
          // u5bf9u4e8eu975e USDT u8d44u4ea7uff0cu4f7fu7528u4ea4u6613u4ef7u683cu8ba1u7b97USDTu4ef7u503c
          if (['BTC', 'ETH', 'BNB', 'SOL', 'DOGE', 'XRP'].includes(trade.commissionAsset)) {
            const estimatedUsdtValue = parseFloat(trade.commission || 0) * parseFloat(trade.price || 0);
            total += estimatedUsdtValue;
          }
        }
      }
    });
    
    return total;
  });
  
  // u53e6u5916u589eu52a0u4ea4u6613u7c7bu578bu7edf u8ba1 (u4e70u5165/u5356u51fa)
  const tradeTypeStats = computed(() => {
    if (!marginTrades.value || marginTrades.value.length === 0) {
      return { buy: 0, sell: 0 };
    }
    
    let buyCount = 0;
    let sellCount = 0;
    
    marginTrades.value.forEach(trade => {
      if (trade.isBuyer) {
        buyCount++;
      } else {
        sellCount++;
      }
    });
    
    return { buy: buyCount, sell: sellCount };
  });
  
  // u7edf u8ba1 Maker/Taker u6570u91cf
  const makerTakerStats = computed(() => {
    if (!marginTrades.value || marginTrades.value.length === 0) {
      return { maker: 0, taker: 0 };
    }
    
    let makerCount = 0;
    let takerCount = 0;
    
    marginTrades.value.forEach(trade => {
      if (trade.isMaker) {
        makerCount++;
      } else {
        takerCount++;
      }
    });
    
    return { maker: makerCount, taker: takerCount };
  });
  
  // u683cu5f0fu5316u603bu8ba1u7b97u5c5eu6027u624bu7eedu8d39
  const totalCommissionFormatted = computed(() => {
    return totalCommission.value.toFixed(6) + ' USDT';
  });
  
  // u83b7u53d6u6309u4ea4u6613u5bf9u5206u7ec4u7684u624bu7eedu8d39
  const getCommissionBySymbol = (symbol) => {
    if (!marginTrades.value || marginTrades.value.length === 0) return 0;
    if (!symbol) return 0;
    
    const symbolTrades = marginTrades.value.filter(trade => trade.symbol === symbol);
    
    let total = 0;
    symbolTrades.forEach(trade => {
      if (trade.commission) {
        if (trade.commissionAsset === 'USDT') {
          total += parseFloat(trade.commission || 0);
        } else if (trade.commissionAsset && trade.price) {
          if (['BTC', 'ETH', 'BNB', 'SOL', 'DOGE', 'XRP'].includes(trade.commissionAsset)) {
            const estimatedUsdtValue = parseFloat(trade.commission || 0) * parseFloat(trade.price || 0);
            total += estimatedUsdtValue;
          }
        }
      }
    });
    
    return total;
  };
  
  // u83b7u53d6u6309u5b50u8d26u53f7u5206u7ec4u7684u624bu7eedu8d39
  const getCommissionByAccount = (email) => {
    if (!marginTrades.value || marginTrades.value.length === 0) return 0;
    if (!email) return 0;
    
    const accountTrades = marginTrades.value.filter(trade => trade.email === email);
    
    let total = 0;
    accountTrades.forEach(trade => {
      if (trade.commission) {
        if (trade.commissionAsset === 'USDT') {
          total += parseFloat(trade.commission || 0);
        } else if (trade.commissionAsset && trade.price) {
          if (['BTC', 'ETH', 'BNB', 'SOL', 'DOGE', 'XRP'].includes(trade.commissionAsset)) {
            const estimatedUsdtValue = parseFloat(trade.commission || 0) * parseFloat(trade.price || 0);
            total += estimatedUsdtValue;
          }
        }
      }
    });
    
    return total;
  };

  // u67e5u8be2u6760u6746u4ea4u6613u7684u65b9u6cd5
  const fetchMarginTrades = async (params = {}) => {
    if (isLoading.value) return marginTrades.value;

    // u68c0u67e5u7f13u5b58u662fu5426u8fd8u6709u6548
    const now = Date.now();
    const useCache = params.useCache !== false && 
                    lastUpdateTime.value && 
                    (now - lastUpdateTime.value < CACHE_DURATION);

    if (useCache) {
      console.log('u4f7fu7528u7f13u5b58u6760u6746u624bu7eedu8d39u6570u636euff0cu6761u76eeu6570u91cf', marginTrades.value.length, 'u6761');
      return marginTrades.value;
    }

    isLoading.value = true;
    errorMessage.value = '';

    try {
      // u83b7u53d6u7528u6237u4fe1u606f
      const user = getCurrentUser();
      if (!user || !user.token) {
        throw new Error('u672au767bu5f55u6216u767bu5f55u5df2u8fc7u671f');
      }

      const emails = params.emails || [];
      const symbols = params.symbols || params.symbol ? [params.symbol] : ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'DOGEUSDT', 'SOLUSDT'];
      const limit = params.limit || 500;
      const startTime = params.startTime || params.queryStartTime || undefined;

      if (!emails || emails.length === 0) {
        throw new Error('u672au9009u62e9u5b50u8d26u53f7');
      }

      // u4e3au6bcfu4e2au5b50u8d26u53f7u548cu4ea4u6613u5bf9u7ec4u5408u53d1u9001u591au4e2au8bf7u6c42
      let allTrades = [];
      const requests = [];

      for (const email of emails) {
        for (const symbol of symbols) {
          const requestData = {
            email: email,
            symbol: symbol,
            limit: limit,
            user_id: user.id
          };
          
          if (startTime) {
            requestData.startTime = startTime;
          }

          requests.push(
            axios.post('/api/margin/trades', requestData, {
              headers: {
                'Authorization': `Bearer ${user.token}`
              }
            })
          );
        }
      }

      // u5e76u884cu53d1u9001u6240u6709u8bf7u6c42
      const responses = await Promise.allSettled(requests);

      responses.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value.data && result.value.data.success) {
          const trades = result.value.data.data || [];
          // u6dfbu52a0 u5b50u8d26u53f7u548cu4ea4u6613u5bf9u4fe1u606f
          const emailIndex = Math.floor(index / symbols.length);
          const symbolIndex = index % symbols.length;
          const currentEmail = emails[emailIndex];
          const currentSymbol = symbols[symbolIndex];

          trades.forEach(trade => {
            allTrades.push({
              ...trade,
              email: currentEmail,
              symbol: trade.symbol || currentSymbol,
              // u786eu4fddu5173u952eu5b57u6bb5u90fdu5b58u5728
              isBuyer: !!trade.isBuyer,
              isMaker: !!trade.isMaker,
              price: trade.price || '0',
              commission: trade.commission || '0',
              commissionAsset: trade.commissionAsset || '',
              time: trade.time || Date.now(),
              id: trade.id || `${Date.now()}-${Math.random().toString(36).substring(2, 10)}`
            });
          });
        }
      });

      // u5bf9u7ed3u679cu8fdbu884cu5904u7406
      marginTrades.value = allTrades;
      lastUpdateTime.value = now;

      console.log(`u83b7u53d6u6760u6746u4ea4u6613u624bu7eedu8d39u6570u636eu6210u529fuff0cu5171 ${allTrades.length} u6761u4ea4u6613u8bb0u5f55`);
      return marginTrades.value;

    } catch (error) {
      console.error('u83b7u53d6u6760u6746u624bu7eedu8d39u5931u8d25:', error);
      errorMessage.value = error.message || 'u83b7u53d6u6760u6746u624bu7eedu8d39u5931u8d25';
      return [];
    } finally {
      isLoading.value = false;
    }
  };
  
  // u68c0u67e5u662fu5426u6709u6760u6746u6210u4ea4u8bb0u5f55
  const hasMarginTrades = computed(() => {
    return marginTrades.value.length > 0;
  });

  // u6e05u9664u7f13u5b58u6570u636eu7684u65b9u6cd5
  const clearCache = () => {
    marginTrades.value = [];
    lastUpdateTime.value = null;
    console.log('u5df2u6e05u9664u6760u6746u624bu7eedu8d39u7f13u5b58');
  };

  return {
    // u72b6u6001
    marginTrades,
    isLoading,
    lastUpdateTime,
    errorMessage,
    
    // u8ba1u7b97u5c5eu6027
    totalCommission,
    totalCommissionFormatted,
    tradeTypeStats,
    makerTakerStats,
    hasMarginTrades,
    
    // u65b9u6cd5u5bfcu51fa
    fetchMarginTrades,
    clearCache,
    getCommissionBySymbol,
    getCommissionByAccount
  };
}); 