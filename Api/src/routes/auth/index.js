import express from "express";
import loginRoute from "./login.js";
import callbackRoute from "./callback.js";
import sessionRoute from "./session.js";
import logoutRoute from "./logout.js";
import emailLoginRoute from "./email-login.js";

const router = express.Router();
router.use("/login", loginRoute);
router.use("/callback", callbackRoute);
router.use("/session", sessionRoute);
router.use("/logout", logoutRoute);
router.use("/email", emailLoginRoute);

export default router;