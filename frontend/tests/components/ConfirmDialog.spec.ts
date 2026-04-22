import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import ConfirmDialog from '@/components/admin/ConfirmDialog.vue'
import en from '@/i18n/locales/en.json'

function makeWrapper() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(ConfirmDialog, {
    props: { title: 'Delete item', message: 'Are you sure?' },
    global: { plugins: [i18n], stubs: { Teleport: true } },
    attachTo: document.body,
  })
}

describe('ConfirmDialog', () => {
  it('renders title and message', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('Delete item')
    expect(wrapper.text()).toContain('Are you sure?')
  })

  it('emits confirm on confirm button click', async () => {
    const wrapper = makeWrapper()
    const btn = wrapper.findAll('button').find(b => b.text() === 'Confirm')
    await btn!.trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
  })

  it('emits cancel on cancel button click', async () => {
    const wrapper = makeWrapper()
    const btn = wrapper.findAll('button').find(b => b.text() === 'Cancel')
    await btn!.trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('emits cancel on overlay click', async () => {
    const wrapper = makeWrapper()
    const overlay = wrapper.find('.confirm-overlay')
    await overlay.trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })
})
