// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import PluginFormModal from '@/components/admin/PluginFormModal.vue'
import en from '@/i18n/locales/en.json'

const availablePlugins = [
  {
    plugin_type: 'telegram',
    label: 'Telegram',
    description: 'Send Telegram notifications',
    config_schema: {
      bot_token: { type: 'str', required: true, secret: true, label: 'Bot Token', description: 'Token from BotFather' },
      chat_id: { type: 'str', required: true, secret: false, label: 'Chat ID', description: 'Chat/group/channel ID' },
      notify_events: { type: 'list', required: false, secret: false, label: 'Events', default: ['new_article', 'digest_ready'] },
    },
  },
]

function makeWrapper(plugin = null) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(PluginFormModal, {
    props: { plugin, available: availablePlugins },
    global: { plugins: [i18n], stubs: { Teleport: true } },
    attachTo: document.body,
  })
}

describe('PluginFormModal', () => {
  it('generates fields from schema when type selected', async () => {
    const wrapper = makeWrapper()
    const select = wrapper.find('select')
    await select.setValue('telegram')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Bot Token')
    expect(wrapper.text()).toContain('Chat ID')
  })

  it('secret fields use password input', async () => {
    const wrapper = makeWrapper()
    const select = wrapper.find('select')
    await select.setValue('telegram')
    await wrapper.vm.$nextTick()
    const inputs = wrapper.findAll('input[type="password"]')
    expect(inputs.length).toBeGreaterThan(0)
  })

  it('non-secret fields use text input', async () => {
    const wrapper = makeWrapper()
    const select = wrapper.find('select')
    await select.setValue('telegram')
    await wrapper.vm.$nextTick()
    // chat_id is not secret → text input
    const textInputs = wrapper.findAll('input[type="text"]')
    expect(textInputs.length).toBeGreaterThan(0)
  })

  it('list fields render as checkboxes', async () => {
    const wrapper = makeWrapper()
    const select = wrapper.find('select')
    await select.setValue('telegram')
    await wrapper.vm.$nextTick()
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes.length).toBeGreaterThan(0)
  })
})
