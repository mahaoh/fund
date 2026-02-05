import { createApp } from "vue";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import FundList from "./pages/FundList.vue";
import FundDetail from "./pages/FundDetail.vue";
import "./styles.css";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", component: FundList },
    { path: "/fund/:code", component: FundDetail, props: true },
  ],
});

createApp(App).use(router).mount("#app");
