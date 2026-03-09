<script setup>
import { onBeforeUnmount, ref } from 'vue'
import axios from 'axios'

const resumePictureApi = 'http://127.0.0.1:8000/user/resume-picture'

const fileInputRef = ref(null)
const selectedFile = ref(null)
const previewUrl = ref('')
const isUploading = ref(false)

const resetPreviewUrl = () => {
	if (previewUrl.value) {
		URL.revokeObjectURL(previewUrl.value)
		previewUrl.value = ''
	}
}

const triggerFilePicker = () => {
	fileInputRef.value?.click()
}

const onFileChange = (event) => {
	const [file] = event.target.files || []

	resetPreviewUrl()
	selectedFile.value = null

	if (!file) {
		return
	}

	if (!file.type.startsWith('image/')) {
		window.alert('请选择图片文件')
		event.target.value = ''
		return
	}

	selectedFile.value = file
	previewUrl.value = URL.createObjectURL(file)
}

const onUpload = async () => {
	if (!selectedFile.value) {
		window.alert('请先选择一张图片')
		return
	}

	console.log('准备上传的简历图片文件:', {
		name: selectedFile.value.name,
		type: selectedFile.value.type,
		size: selectedFile.value.size,
		lastModified: selectedFile.value.lastModified
	})

	const formData = new FormData()
	formData.append('file', selectedFile.value)

	isUploading.value = true

	try {
		// 如出现跨域报错，需由后端在该接口开启 CORS（Access-Control-Allow-Origin 等响应头）。
		const response = await axios.post(resumePictureApi, formData, {
			headers: {
				'Content-Type': 'multipart/form-data'
			}
		})

		console.log('简历图片上传成功:', response.data)
		window.alert('简历图片上传成功')
	} catch (error) {
		console.error('简历图片上传失败:', error)

		const backendMessage = error.response?.data?.message || error.response?.data?.detail
		window.alert(backendMessage || '上传失败，请检查网络或后端接口配置')
	} finally {
		isUploading.value = false
	}
}

onBeforeUnmount(() => {
	resetPreviewUrl()
})
</script>

<template>
	<section class="resume-upload-wrap">
		<h3 class="upload-title">简历图片上传</h3>

		<div class="upload-actions">
			<input ref="fileInputRef" class="hidden-input" type="file" accept="image/*" @change="onFileChange" />
			<button type="button" class="btn secondary" @click="triggerFilePicker">选择图片</button>
			<button type="button" class="btn primary" :disabled="!selectedFile || isUploading" @click="onUpload">
				{{ isUploading ? '上传中...' : '上传图片' }}
			</button>
		</div>

		<p v-if="selectedFile" class="file-name">已选择：{{ selectedFile.name }}</p>

		<div v-if="previewUrl" class="preview-box">
			<img :src="previewUrl" alt="简历图片预览" class="preview-image" />
		</div>
	</section>
</template>

<style scoped>
.resume-upload-wrap {
	margin: 0 0 16px;
	padding: 16px;
	background: #f8fafc;
	border: 1px dashed #cbd5e1;
	border-radius: 10px;
}

.upload-title {
	margin: 0 0 12px;
	font-size: 18px;
	font-weight: 700;
	color: #1f2937;
}

.upload-actions {
	display: flex;
	gap: 10px;
	flex-wrap: wrap;
	align-items: center;
}

.hidden-input {
	display: none;
}

.file-name {
	margin: 10px 0 0;
	font-size: 14px;
	color: #334155;
}

.preview-box {
	margin-top: 12px;
	padding: 8px;
	width: fit-content;
	max-width: 100%;
	background: #ffffff;
	border: 1px solid #dbeafe;
	border-radius: 8px;
}

.preview-image {
	display: block;
	width: min(320px, 100%);
	height: auto;
	border-radius: 6px;
	object-fit: contain;
}

.btn {
	min-width: 100px;
	padding: 10px 16px;
	border-radius: 8px;
	border: none;
	cursor: pointer;
	font-size: 14px;
	font-weight: 600;
}

.btn.primary {
	background: #2563eb;
	color: #ffffff;
}

.btn.primary:hover:enabled {
	background: #1d4ed8;
}

.btn.primary:disabled {
	background: #93c5fd;
	cursor: not-allowed;
}

.btn.secondary {
	background: #e2e8f0;
	color: #111827;
}

.btn.secondary:hover {
	background: #cbd5e1;
}
</style>
