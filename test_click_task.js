// 测试任务切换功能的脚本
console.log('🧪 开始测试任务切换功能...');

// 等待页面完全加载
setTimeout(() => {
    console.log('🔍 查找任务项...');
    
    // 查找所有任务项
    const tasks = document.querySelectorAll('.task-item');
    console.log(`找到 ${tasks.length} 个任务项`);
    
    tasks.forEach((task, index) => {
        console.log(`任务 ${index + 1}:`, {
            taskId: task.dataset.taskId,
            symbol: task.dataset.symbol,
            symbolName: task.dataset.symbolName,
            period: task.dataset.period
        });
    });
    
    // 点击第二个任务 (cu2405)
    if (tasks.length > 1) {
        console.log('🎯 点击第二个任务...');
        const secondTask = tasks[1];
        secondTask.click();
        
        // 等待一秒后检查技术指标是否更新
        setTimeout(() => {
            console.log('✅ 任务切换完成，检查技术指标更新状态...');
            
            // 检查技术指标标题是否更新
            const indicatorTitle = document.getElementById('indicators-title');
            if (indicatorTitle) {
                console.log('📊 技术指标标题:', indicatorTitle.textContent);
            }
            
            // 检查选中状态
            const selectedTask = document.querySelector('.task-item.selected');
            if (selectedTask) {
                console.log('✅ 当前选中任务:', {
                    taskId: selectedTask.dataset.taskId,
                    symbol: selectedTask.dataset.symbol,
                    symbolName: selectedTask.dataset.symbolName
                });
            }
        }, 2000);
    }
}, 3000);