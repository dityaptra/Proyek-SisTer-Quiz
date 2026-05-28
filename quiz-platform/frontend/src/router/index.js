import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import QuizRoom from '../views/QuizRoom.vue'
import Result from '../views/Result.vue'
import Notifications from '../views/Notifications.vue'

const routes = [
  { path: '/',            component: Login },
  { path: '/dashboard',   component: Dashboard, meta: { requiresAuth: true } },
  { path: '/quiz/:id',    component: QuizRoom,  meta: { requiresAuth: true } },
  { path: '/result/:id',  component: Result,    meta: { requiresAuth: true } },
  { path: '/notifications', component: Notifications, meta: { requiresAuth: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const student = localStorage.getItem('student')
  if (to.meta.requiresAuth && !student) {
    next('/')
  } else {
    next()
  }
})

export default router
