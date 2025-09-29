// 测试所有技术指标在不同合约间的动态切换
console.log('🧪 开始全面测试所有技术指标的动态切换功能...');

// 测试数据
const testContracts = [
    { symbol: 'rb2405', name: '螺纹钢', period: '1h' },
    { symbol: 'cu2405', name: '沪铜', period: '30m' },
    { symbol: 'al2405', name: '沪铝', period: '1h' }
];

const indicators = ['macd', 'rsi', 'kdj', 'bollinger'];

async function testIndicatorForContract(contract, indicator) {
    try {
        console.log(`🔍 测试 ${contract.name}(${contract.symbol}) ${indicator.toUpperCase()} 指标...`);
        
        const apiUrl = `/api/futures/technical_indicators?symbol=${contract.symbol}&period=${contract.period}&limit=50&indicators=${indicator}`;
        console.log(`📡 API调用: ${apiUrl}`);
        
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        if (data.success && data.indicators[indicator]) {
            const indicatorData = data.indicators[indicator];
            let testResult = '';
            
            switch (indicator) {
                case 'macd':
                    const dif = indicatorData.dif && indicatorData.dif.length > 0 ? indicatorData.dif.slice(-1)[0] : null;
                    testResult = `DIF=${dif?.toFixed(3) || '无数据'}`;
                    break;
                case 'rsi':
                    const rsi = indicatorData.values && indicatorData.values.length > 0 ? indicatorData.values.slice(-1)[0] : null;
                    testResult = `RSI=${rsi?.toFixed(2) || '无数据'}`;
                    break;
                case 'kdj':
                    const k = indicatorData.k && indicatorData.k.length > 0 ? indicatorData.k.slice(-1)[0] : null;
                    testResult = `K线=${k?.toFixed(2) || '无数据'}`;
                    break;
                case 'bollinger':
                    const upper = indicatorData.upper && indicatorData.upper.length > 0 ? indicatorData.upper.slice(-1)[0] : null;
                    testResult = `上轨=${upper?.toFixed(2) || '无数据'}`;
                    break;
            }
            
            console.log(`✅ ${contract.name} ${indicator.toUpperCase()}: ${testResult}`);
            return { success: true, contract: contract.name, indicator: indicator.toUpperCase(), result: testResult };
        } else {
            console.log(`❌ ${contract.name} ${indicator.toUpperCase()}: 数据获取失败`);
            return { success: false, contract: contract.name, indicator: indicator.toUpperCase(), error: '数据获取失败' };
        }
    } catch (error) {
        console.log(`❌ ${contract.name} ${indicator.toUpperCase()}: ${error.message}`);
        return { success: false, contract: contract.name, indicator: indicator.toUpperCase(), error: error.message };
    }
}

async function runFullTest() {
    console.log('🚀 开始执行全面测试...');
    const results = [];
    
    for (const contract of testContracts) {
        console.log(`\n📊 === 测试 ${contract.name}(${contract.symbol}) ===`);
        
        for (const indicator of indicators) {
            const result = await testIndicatorForContract(contract, indicator);
            results.push(result);
            
            // 短暂延迟避免请求过快
            await new Promise(resolve => setTimeout(resolve, 200));
        }
    }
    
    // 汇总结果
    console.log('\n🎯 === 测试结果汇总 ===');
    const successCount = results.filter(r => r.success).length;
    const totalCount = results.length;
    
    console.log(`✅ 成功: ${successCount}/${totalCount} (${(successCount/totalCount*100).toFixed(1)}%)`);
    
    // 显示详细结果
    console.table(results);
    
    if (successCount === totalCount) {
        console.log('🎉 所有技术指标测试通过！动态切换功能完全正常！');
    } else {
        console.log('⚠️ 部分指标测试失败，需要进一步检查');
    }
    
    return results;
}

// 等待页面加载完成后执行测试
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runFullTest);
} else {
    runFullTest();
}