/**
 * EyeExam Landing Page Script
 * Handles form submission, mobile menu, and smooth scrolling
 */

/* eslint-env browser */

(function () {
  'use strict';

  // DOM Ready
  document.addEventListener('DOMContentLoaded', function () {
    initMobileMenu();
    initWaitlistForm();
    initSmoothScroll();
    initScrollAnimations();
  });

  /**
   * Mobile Menu Toggle
   */
  function initMobileMenu() {
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    const body = document.body;

    if (!menuBtn || !navLinks) return;

    menuBtn.addEventListener('click', function () {
      this.classList.toggle('active');
      navLinks.classList.toggle('active');
      body.classList.toggle('menu-open');
    });

    // Close menu when clicking a link
    const links = navLinks.querySelectorAll('a');
    links.forEach(function (link) {
      link.addEventListener('click', function () {
        menuBtn.classList.remove('active');
        navLinks.classList.remove('active');
        body.classList.remove('menu-open');
      });
    });
  }

  /**
   * Email Validation
   */
  function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  /**
   * Waitlist Form Handling
   */
  function initWaitlistForm() {
    const form = document.getElementById('waitlistForm');
    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const emailInput = document.getElementById('email');
      const messageEl = document.getElementById('formMessage');
      const submitBtn = form.querySelector('button[type="submit"]');

      const email = emailInput.value.trim();

      // Helper to show messages
      function showMessage(text, type) {
        if (!messageEl) return;
        messageEl.textContent = text;
        messageEl.className = 'form-message ' + type;
      }

      // Basic email validation
      if (!email || !isValidEmail(email)) {
        showMessage('Please enter a valid email address.', 'error');
        return;
      }

      // Disable button during submission
      submitBtn.disabled = true;
      submitBtn.textContent = 'Joining...';

      // Submit to Cloudflare Worker
      fetch('https://eyeexam-waitlist.zhuhuilin.workers.dev/join', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email }),
      })
        .then(function (response) {
          if (response.ok) {
            showMessage("Thank you! You've been added to the waitlist.", 'success');
            emailInput.value = '';
          } else {
            return response.json().then(function (data) {
              throw new Error(data.error || 'Failed to join waitlist');
            });
          }
        })
        .catch(function (_err) {
          // Fallback: Show message with email option
          showMessage('Thank you! Click below to send your request.', 'success');

          // Create a fallback link
          const subject = encodeURIComponent('EyeExam Waitlist Request');
          const body = encodeURIComponent(
            'Please add me to the EyeExam waitlist.\n\nEmail: ' +
              email +
              "\n\nI'm interested in early access."
          );

          const fallbackLink = document.createElement('a');
          fallbackLink.href = 'mailto:contact@ibetter.ai?subject=' + subject + '&body=' + body;
          fallbackLink.textContent = 'Click here to confirm via email';
          fallbackLink.style.cssText =
            'display: inline-block; margin-top: 8px; color: #00d4aa; text-decoration: underline;';

          if (messageEl) {
            messageEl.appendChild(document.createElement('br'));
            messageEl.appendChild(fallbackLink);
          }
        })
        .finally(function () {
          submitBtn.disabled = false;
          submitBtn.innerHTML = 'Join Waitlist';
        });
    });
  }

  /**
   * Smooth Scroll for Anchor Links
   */
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
      anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (!href || href === '#') return;

        const target = document.querySelector(href);
        if (!target) return;

        e.preventDefault();

        const navbar = document.querySelector('.navbar');
        const navbarHeight = navbar ? navbar.offsetHeight : 0;
        const targetPosition =
          target.getBoundingClientRect().top + window.pageYOffset - navbarHeight;

        window.scrollTo({
          top: targetPosition,
          behavior: 'smooth',
        });
      });
    });
  }

  /**
   * Scroll Animations using Intersection Observer
   */
  function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.feature-card, .step, .section-header');

    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px',
      }
    );

    animatedElements.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
      observer.observe(el);
    });
  }

  /**
   * Navbar background on scroll
   */
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', function () {
      const currentScrollY = window.scrollY;

      if (currentScrollY > 50) {
        navbar.style.background = 'rgba(10, 22, 40, 0.95)';
      } else {
        navbar.style.background = 'rgba(10, 22, 40, 0.8)';
      }
    });
  }
})();
