<!-- src/App.vue -->
<template>
  <div class="app-root">
    <router-view />
  </div>
</template>

<script setup>
// 不要 import 任何业务组件！
</script>

<style scoped>
.app-root {
  min-height: 100vh;
  padding: 20px 12px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}
</style>