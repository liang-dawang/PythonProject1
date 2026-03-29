<script setup>
import { reactive, computed } from 'vue'
import axios from 'axios'
import ResumeUpload from './ResumeUpload.vue'
import JobMatchingButton from './JobMatchingButton.vue'

const resumeTextApi = 'http://127.0.0.1:8000/user/resume-text'

const educationOptions = ['大专及以下', '大专', '本科', '硕士', '博士']

const desiredJobOptions = [
	'C/C++',
	'Java',
	'前端开发',
	'实施工程师',
	'技术支持与运维',
	'测试工程师',
	'硬件测试',
	'科研人员',
	'软件测试',
	'项目经理/主管'
]

const skillLevelOptions = ['入门', '基础', '熟练', '精通']

const internshipDurationOptions = [
	'一年以内',
	'一到三年',
	'三年及以上'
	
]

const formData = reactive({
	name: '',
	education: '',
	major: '',
	desiredJob: '',
	coreSkill: '',
	certificate: '',
	desiredSalary: '',
	skillLevel: '',
	stackDetail: '',
	innovation: '',
	learning: '',
	pressureResistance: '',
	communication: '',
	internshipProject: '',
	internshipDuration: '',
	projectAchievement: ''
})

const requiredFields = {
	name: '姓名',
	education: '学历',
	major: '专业',
	desiredJob: '求职意向岗位',
	coreSkill: '核心技能',
	internshipDuration: '相关工作时长'
}

const missingRequiredFields = computed(() => {
	return Object.entries(requiredFields)
		.filter(([key]) => !String(formData[key]).trim())
		.map(([, label]) => label)
})

const onSubmit = async () => {
	if (missingRequiredFields.value.length > 0) {
		window.alert(`请先填写必填项：${missingRequiredFields.value.join('、')}`)
		return
	}

	const payload = {
		name: formData.name,
		education: formData.education,
		major: formData.major,
		desiredJob: formData.desiredJob,
		coreSkill: formData.coreSkill,
		certificate: formData.certificate,
		desiredSalary: formData.desiredSalary,
		skillLevel: formData.skillLevel,
		stackDetail: formData.stackDetail,
		innovation: formData.innovation,
		learning: formData.learning,
		pressureResistance: formData.pressureResistance,
		communication: formData.communication
	}

	console.log('提交简历文本数据:', payload)

	try {
		// 如果浏览器提示跨域错误，需要后端为该接口配置 CORS（Access-Control-Allow-Origin）。
		const response = await axios.post(resumeTextApi, payload)
		console.log('简历文本提交成功:', response.data)
		window.alert('简历信息已填写完成')
	} catch (error) {
		console.error('简历文本提交失败:', error)
		window.alert('提交失败，请检查网络或后端接口配置')
	}
}

const onReset = () => {
	Object.keys(formData).forEach((key) => {
		formData[key] = ''
	})
}
</script>

<template>
	<!-- <main class="page">
     <ResumeForm />
    <JobMatchingButton /> 
   </main>  -->
	<section class="resume-form-wrap">
		<h2 class="title">简历信息录入表</h2>
		<p class="subtitle">标注 <span class="required-mark">*</span> 的字段为必填项</p>
		<ResumeUpload />

		<form class="resume-form" @submit.prevent="onSubmit">
			<table class="resume-table" cellspacing="0" cellpadding="0">
				<tbody>
					<tr>
						<th>
							姓名 <span class="required-mark">*</span>
						</th>
						<td>
							<input v-model.trim="formData.name" type="text" placeholder="请输入姓名" />
						</td>
						<th>
							学历 <span class="required-mark">*</span>
						</th>
						<td>
							<select v-model="formData.education">
								<option value="">请选择学历</option>
								<option v-for="item in educationOptions" :key="item" :value="item">{{ item }}</option>
							</select>
						</td>
					</tr>

					<tr>
						<th>
							专业 <span class="required-mark">*</span>
						</th>
						<td>
							<input v-model.trim="formData.major" type="text" placeholder="请输入专业" />
						</td>
						<th>
							求职意向岗位 <span class="required-mark">*</span>
						</th>
						<td>
							<select v-model="formData.desiredJob">
								<option value="">请选择意向岗位</option>
								<option v-for="item in desiredJobOptions" :key="item" :value="item">{{ item }}</option>
							</select>
						</td>
					</tr>

					<tr>
						<th>
							核心技能 <span class="required-mark">*</span>
						</th>
						<td colspan="3">
							<input v-model.trim="formData.coreSkill" type="text" placeholder="请输入核心技能（多个技能可用逗号分隔）" />
						</td>
					</tr>

					<tr>
						<th>证书</th>
						<td>
							<input v-model.trim="formData.certificate" type="text" placeholder="如：软考中级、CET-6" />
						</td>
						<th>薪资预期</th>
						<td>
							<input v-model.trim="formData.desiredSalary" type="text" placeholder="如：12k-18k" />
						</td>
					</tr>

					<tr>
						<th>技能熟练度</th>
						<td>
							<select v-model="formData.skillLevel">
								<option value="">请选择熟练度</option>
								<option v-for="item in skillLevelOptions" :key="item" :value="item">{{ item }}</option>
							</select>
						</td>
						<th>相关工作时长<span class="required-mark">*</span></th>
						<td>
							<select v-model="formData.internshipDuration">
								<option value="">请选择相关工作时长</option>
								<option v-for="item in internshipDurationOptions" :key="item" :value="item">{{ item }}</option>
							</select>
						</td>
					</tr>

					<tr>
						<th>技术栈详情</th>
						<td colspan="3">
							<textarea
								v-model.trim="formData.stackDetail"
								rows="3"
								placeholder="补充技能描述，如框架、工具链、擅长场景"
							></textarea>
						</td>
					</tr>

					<tr>
						<th>创新能力</th>
						<td colspan="3">
							<textarea v-model.trim="formData.innovation"
							 rows="3" 
							 placeholder="请描述你的创新能力（示例：优化项目接口，提效30%/提出AI编程工具落地方案/申请XX技术专利/发表XX方向论文）"></textarea>
						</td>
					</tr>

					<tr>
						<th>学习能力</th>
						<td colspan="3">
							<textarea v-model.trim="formData.learning" 
							rows="3"
							 placeholder="请描述你的学习能力（示例：1周掌握Vue3新特性/自主学习微服务架构并落地项目/通过Java高级认证/阅读官方文档解决技术问题）"></textarea>
						</td>
					</tr>

					<tr>
						<th>抗压能力</th>
						<td colspan="3">
							<textarea v-model.trim="formData.pressureResistance" 
							rows="3" 
							placeholder="请描述你的抗压能力（示例：能接受适度加班/可同时处理3个并行任务/完成过紧急交付的项目/应对过高强度客户需求）"></textarea>
						</td>
					</tr>

					<tr>
						<th>沟通能力</th>
						<td colspan="3">
							<textarea v-model.trim="formData.communication" 
							rows="3"
							 placeholder="请描述你的沟通能力（示例：能独立对接客户需求/跨部门协作顺畅/可编写清晰的技术文档/日语沟通流利）"></textarea>
						</td>
					</tr>

					<tr>
						<th>实习/项目经历</th>
						<td colspan="3">
							<textarea
								v-model.trim="formData.internshipProject"
								rows="4"
								placeholder="请描述实习或项目背景、职责和技术要点"
							></textarea>
						</td>
					</tr>

					<tr>
						<th>项目成果</th>
						<td colspan="3">
							<textarea
								v-model.trim="formData.projectAchievement"
								rows="4"
								placeholder="请描述结果数据、业务价值或技术产出"
							></textarea>
						</td>
					</tr>
				</tbody>
			</table>

			<div class="actions">
				<button type="button" class="btn secondary" @click="onReset">重置</button>
				<button type="submit" class="btn primary">提交</button>
			</div>
		</form>
	</section>
	  <JobMatchingButton />
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 20px 12px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}
.resume-form-wrap {
	max-width: 980px;
	margin: 28px auto;
	padding: 24px;
	background: #ffffff;
	border: 1px solid #e5e7eb;
	border-radius: 12px;
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
}

.title {
	margin: 0;
	font-size: 24px;
	font-weight: 700;
	color: #111827;
}

.subtitle {
	margin: 8px 0 18px;
	color: #4b5563;
}

.required-mark {
	color: #dc2626;
}

.resume-form {
	width: 100%;
}

.resume-table {
	width: 100%;
	border-collapse: collapse;
	table-layout: fixed;
	border: 1px solid #d1d5db;
}

.resume-table th,
.resume-table td {
	border: 1px solid #d1d5db;
	padding: 12px;
	vertical-align: middle;
}

.resume-table th {
	width: 20%;
	background: #f3f4f6;
	color: #111827;
	text-align: left;
	font-weight: 600;
}

.resume-table td {
	width: 30%;
	background: #fff;
}

input,
select,
textarea {
	width: 100%;
	border: 1px solid #cbd5e1;
	border-radius: 8px;
	padding: 10px 12px;
	font-size: 14px;
	color: #111827;
	outline: none;
	box-sizing: border-box;
	background: #ffffff;
}

textarea {
	resize: vertical;
	min-height: 84px;
}

input:focus,
select:focus,
textarea:focus {
	border-color: #2563eb;
	box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.actions {
	display: flex;
	justify-content: flex-end;
	gap: 12px;
	margin-top: 16px;
}

.btn {
	min-width: 96px;
	padding: 10px 16px;
	border-radius: 8px;
	border: none;
	cursor: pointer;
	font-size: 14px;
	font-weight: 600;
}

.btn.primary {
	background: #2563eb;
	color: #fff;
}

.btn.primary:hover {
	background: #1d4ed8;
}

.btn.secondary {
	background: #e5e7eb;
	color: #111827;
}

.btn.secondary:hover {
	background: #d1d5db;
}

@media (max-width: 768px) {
	.resume-form-wrap {
		margin: 12px;
		padding: 14px;
	}

	.resume-table,
	.resume-table tbody,
	.resume-table tr,
	.resume-table th,
	.resume-table td {
		display: block;
		width: 100%;
	}

	.resume-table tr {
		border-bottom: 1px solid #d1d5db;
	}

	.resume-table th {
		border-bottom: none;
	}

	.resume-table td {
		border-top: none;
	}
}
</style>