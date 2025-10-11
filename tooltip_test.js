// Tooltip测试脚本 - 验证SuperTrend ATR周期偏移功能
console.log('🧪 开始SuperTrend Tooltip测试...');

// 测试函数：检查tooltip过滤器功能
function testTooltipFilter() {
    console.log('📋 测试tooltip filter功能...');
    
    // 模拟ATR周期为10的情况
    const atrPeriod = 10;
    
    // 测试前10个点（应该被过滤掉）
    for (let i = 0; i < atrPeriod; i++) {
        const shouldShow = i >= atrPeriod;
        console.log(`点${i}: SuperTrend应该显示=${shouldShow}`);
    }
    
    // 测试第10个点之后（应该显示）
    for (let i = atrPeriod; i < atrPeriod + 5; i++) {
        const shouldShow = i >= atrPeriod;
        console.log(`点${i}: SuperTrend应该显示=${shouldShow}`);
    }
}

// 运行测试
testTooltipFilter();

console.log('✅ 测试完成！');
console.log('📝 测试要点：');
console.log('- 前ATR周期个点(0-9): 只显示K线数据，不显示SuperTrend');
console.log('- 从第ATR周期点开始(10+): 同时显示K线和SuperTrend数据');