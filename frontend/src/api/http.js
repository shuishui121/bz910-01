import axios from 'axios'

const http = axios.create({ baseURL: '/api/v1', timeout: 15000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 统一解包 {code,data,message};409 冲突原样抛给业务组件处理
http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      const err = new Error(body.message)
      err.code = body.code
      err.data = body.data
      return Promise.reject(err)
    }
    return body
  },
  (error) => {
    const body = error.response?.data
    const err = new Error(body?.message || error.message || '网络异常')
    err.httpStatus = error.response?.status
    err.code = body?.code
    err.data = body?.data
    if (err.httpStatus === 401) {
      localStorage.removeItem('token')
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    return Promise.reject(err)
  },
)

export default http
